import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from roadeye import analytics, auth
from roadeye import models as m
from roadeye import services as s
from roadeye.config import settings
from roadeye.contracts import (
    CameraConfig,
    Control,
    Decision,
    EdgeConfig,
    Input,
    Login,
    Receipt,
    Result,
    Review,
    RunCreate,
    TrajectoryQuery,
    WatchCreate,
    Window,
)
from roadeye.db import now, session
from roadeye.evidence import LocalEvidenceStore, digest
from roadeye.plates import normalize
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

app = FastAPI(title="RoadEye synthetic engineering console", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-RoadEye", "X-Correlation-ID"],
)
DB = Annotated[Session, Depends(session)]
User = Annotated[str, Depends(auth.identity)]
Investigator = Annotated[str, Depends(auth.investigator)]
Admin = Annotated[str, Depends(auth.admin)]
Approver = Annotated[str, Depends(auth.approver)]
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=120)]
logger = logging.getLogger("roadeye.api")


@app.middleware("http")
async def boundary(request: Request, call_next):
    correlation = request.headers.get("x-correlation-id", str(uuid4()))[:80]
    request.state.correlation = correlation
    if request.method in ("POST", "PUT", "DELETE"):
        if request.headers.get("x-roadeye") != "console":
            return JSONResponse(
                status_code=403,
                content={"error": "WRITE_HEADER_REQUIRED", "correlation_id": correlation},
            )
        origin = request.headers.get("origin")
        if origin and origin != settings.cors_origin:
            return JSONResponse(
                status_code=403, content={"error": "ORIGIN_DENIED", "correlation_id": correlation}
            )
        body = await request.body()
        if len(body) > 128_000:
            return JSONResponse(
                status_code=413, content={"error": "INPUT_TOO_LARGE", "correlation_id": correlation}
            )
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "status": response.status_code,
                "correlation_id": correlation,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    )
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "correlation_id": request.state.correlation},
    )


@app.exception_handler(RequestValidationError)
async def invalid(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "fields": [".".join(map(str, e["loc"])) for e in exc.errors()],
            "correlation_id": request.state.correlation,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logger.error(
        json.dumps(
            {
                "event": "database.failure",
                "type": type(exc).__name__,
                "correlation_id": request.state.correlation,
            }
        )
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": "DATABASE_UNAVAILABLE_OR_CONSTRAINT",
            "correlation_id": request.state.correlation,
        },
    )


def output(value) -> dict:
    return {"data": value}


def recorded(db: Session, actor: str, operation: str, key: str, payload: dict, action):
    # Transaction-scoped advisory lock serializes the key before result lookup.
    lock_key = int.from_bytes(
        hashlib.sha256(f"{actor}/{operation}/{key}".encode()).digest()[:8], "big", signed=True
    )
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    fingerprint = digest(json.dumps(payload, sort_keys=True, default=str).encode())
    old = db.scalar(
        select(m.Command).where(
            m.Command.actor == actor, m.Command.operation == operation, m.Command.key == key
        )
    )
    if old:
        if old.digest != fingerprint:
            raise HTTPException(409, "IDEMPOTENCY_PAYLOAD_CONFLICT")
        return old.response
    result = jsonable_encoder(action())
    db.add(
        m.Command(actor=actor, operation=operation, key=key, digest=fingerprint, response=result)
    )
    db.commit()
    return result


def local():
    if not settings.demo_enabled:
        raise HTTPException(404, "DEMO_DISABLED")


@app.get("/v1/health/live", response_model=Result)
def live():
    return output({"status": "alive", "source_mode": settings.source_mode})


@app.get("/v1/health/ready", response_model=Result)
def ready(db: DB):
    db.execute(text("SELECT 1 FROM alembic_version"))
    return output(
        {
            "status": "ready",
            "database": "postgresql",
            "postgis": db.scalar(text("SELECT postgis_lib_version()")),
        }
    )


@app.post("/v1/auth/login", response_model=Result)
def login(body: Login, response: Response, db: DB):
    result = auth.login(body, response, db)
    s.audit(db, body.actor.value, "session.login", body.actor.value)
    db.commit()
    return output(result)


@app.get("/v1/auth/me", response_model=Result)
def me(actor: User):
    return output({"actor": actor, "source_mode": "synthetic"})


@app.post("/v1/auth/logout", response_model=Result)
def logout(request: Request, response: Response, db: DB, actor: User):
    token = request.cookies.get("roadeye_session", "")
    row = db.get(m.LocalSession, hashlib.sha256(token.encode()).hexdigest())
    if row:
        db.delete(row)
    db.commit()
    response.delete_cookie("roadeye_session")
    return output({"logged_out": True})


@app.get("/v1/cameras", response_model=Result)
def cameras(db: DB, actor: User):
    return output([s.serialize(c) for c in db.scalars(select(m.Camera).order_by(m.Camera.id))])


@app.get("/v1/cameras/{camera_id}", response_model=Result)
def camera(camera_id: str, db: DB, actor: User):
    row = db.get(m.Camera, camera_id)
    if not row:
        raise HTTPException(404, "CAMERA_NOT_FOUND")
    return output(
        {
            **s.serialize(row),
            "lanes": [
                s.serialize(lane)
                for lane in db.scalars(select(m.Lane).where(m.Lane.camera_id == camera_id))
            ],
        }
    )


@app.put("/v1/cameras/{camera_id}", response_model=Result)
def configure_camera(camera_id: str, body: CameraConfig, db: DB, actor: Admin, key: Key):
    def action():
        if camera_id not in [f"C{i}" for i in range(1, 7)]:
            raise HTTPException(422, "DEMO_NETWORK_LIMIT")
        s.seed(db)
        row = db.get(m.Camera, camera_id)
        assert row
        for field, value in body.model_dump().items():
            setattr(row, field, value)
        s.audit(db, actor, "camera.configured", camera_id)
        return output(s.serialize(row))

    return recorded(db, actor, f"camera:{camera_id}", key, body.model_dump(), action)


@app.get("/v1/graph", response_model=Result)
def graph(db: DB, actor: User):
    return output(
        {
            "network": "fictional-six",
            "coordinate_system": "fictional schematic units",
            "zones": [s.serialize(z) for z in db.scalars(select(m.Zone))],
            "edges": [s.serialize(e) for e in db.scalars(select(m.Edge))],
        }
    )


@app.put("/v1/graph", response_model=Result)
def configure_edge(body: EdgeConfig, db: DB, actor: Admin, key: Key):
    def action():
        s.seed(db)
        row = db.get(m.Edge, (body.source, body.target))
        if row:
            for field, value in body.model_dump().items():
                setattr(row, field, value)
        else:
            db.add(m.Edge(**body.model_dump()))
        s.audit(db, actor, "graph.configured", f"{body.source}:{body.target}")
        return output({"updated": True, "applies_to": "new runs only"})

    return recorded(db, actor, "edge", key, body.model_dump(), action)


@app.get("/v1/demo/scenarios", response_model=Result)
def scenarios(actor: User):
    local()
    return output(json.loads((s.DATA / "manifest.json").read_text()))


@app.post("/v1/demo/runs", response_model=Result)
def create_run(body: RunCreate, db: DB, actor: Admin, key: Key):
    local()

    def action():
        row = s.create_run(db, body.scenario)
        s.audit(db, actor, "run.created", row.id, row.id)
        return output(s.serialize(row))

    return recorded(db, actor, "run.create", key, body.model_dump(), action)


@app.get("/v1/demo/runs", response_model=Result)
def runs(db: DB, actor: User):
    local()
    return output(
        [
            s.serialize(r)
            for r in db.scalars(select(m.Run).order_by(m.Run.created_at.desc()).limit(50))
        ]
    )


@app.get("/v1/demo/runs/{run_id}", response_model=Result)
def status(run_id: str, db: DB, actor: User):
    local()
    run = s.require_run(db, run_id)
    jobs = db.execute(
        select(m.Job.state, func.count()).where(m.Job.run_id == run_id).group_by(m.Job.state)
    ).all()
    lag = db.scalar(
        select(func.min(m.InputEvent.received_at))
        .join(m.Job, m.Job.id == m.InputEvent.id)
        .where(m.Job.run_id == run_id, m.Job.state != "done")
    )
    return output(
        {
            **s.serialize(run),
            "jobs": {state: count for state, count in jobs},
            "total_events": len(s.scenario_events(run.scenario)),
            "camera_health": s.health(db, run),
            "processing_lag_seconds": (now() - lag).total_seconds() if lag else 0,
        }
    )


@app.post("/v1/demo/runs/{run_id}/control", response_model=Result)
def control(run_id: str, body: Control, db: DB, actor: Admin, key: Key):
    local()

    def action():
        run = s.require_run(db, run_id, lock=True)
        if body.action == "pause":
            run.state = "paused"
        elif body.action == "play":
            run.state = "playing"
        elif body.action == "step":
            run.state = "paused"
            s.emit_next(db, run)
        elif body.action == "replay":
            run.cursor = 0
            run.state = "playing"
        elif body.action == "retry":
            for job in db.scalars(
                select(m.Job).where(m.Job.run_id == run_id, m.Job.state == "poison")
            ):
                job.state, job.attempts, job.available_at = "pending", 0, now()
        s.audit(db, actor, "run." + body.action, run.id, run.id)
        return output(s.serialize(run))

    return recorded(db, actor, f"control:{run_id}", key, body.model_dump(), action)


@app.post("/v1/inputs", response_model=Receipt, status_code=202)
def inputs(body: Input, db: DB, actor: Admin, request: Request, key: Key):
    try:
        result = s.ingest(db, body, actor, key, request.state.correlation)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, type(exc).__name__ + ":INVALID_OR_MISSING_EVIDENCE") from exc
    db.commit()
    return result


@app.get("/v1/observations", response_model=Result)
def observations(
    run_id: str,
    start: datetime,
    end: datetime,
    db: DB,
    actor: Investigator,
    request: Request,
    plate: str = "",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1000),
):
    window = Window.model_validate(dict(run_id=run_id, start=start, end=end))
    s.require_run(db, run_id)
    rows = s.observation_rows(db, run_id, window.start, window.end)
    if plate:
        forms = normalize(plate)
        rows = [r for r in rows if r["plate"] in forms]
    s.audit(db, actor, "observations.search", run_id, run_id, request.state.correlation)
    db.commit()
    return output({"items": rows[offset : offset + limit], "total": len(rows), "offset": offset})


@app.get("/v1/observations/{observation_id}", response_model=Result)
def observation(observation_id: str, db: DB, actor: Investigator, request: Request):
    row = db.get(m.Observation, observation_id)
    if not row:
        raise HTTPException(404, "OBSERVATION_NOT_FOUND")
    event = db.get(m.InputEvent, row.input_id)
    passage = db.get(m.Passage, row.passage_id)
    s.audit(db, actor, "observation.read", row.id, row.run_id, request.state.correlation)
    db.commit()
    return output(
        {
            **s.serialize(row),
            "original_input": s.serialize(event),
            "passage": s.serialize(passage),
            "revisions": [
                s.serialize(r)
                for r in db.scalars(
                    select(m.Revision)
                    .where(m.Revision.observation_id == row.id)
                    .order_by(m.Revision.number)
                )
            ],
        }
    )


@app.get("/v1/evidence/{evidence_id}")
def evidence(evidence_id: str, db: DB, actor: Investigator, request: Request):
    row = db.get(m.Evidence, evidence_id)
    if not row:
        raise HTTPException(404, "EVIDENCE_NOT_FOUND")
    try:
        content = LocalEvidenceStore(settings.evidence_root).read(row.object_key)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(404, "EVIDENCE_OBJECT_MISSING") from exc
    if digest(content) != row.digest or len(content) != row.size:
        raise HTTPException(409, "EVIDENCE_INTEGRITY_FAILURE")
    s.audit(db, actor, "evidence.read", row.id, row.run_id, request.state.correlation)
    db.commit()
    return Response(
        content,
        media_type=row.media_type,
        headers={
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Evidence-SHA256": row.digest,
        },
    )


@app.post("/v1/trajectories", response_model=Result)
def trajectories(body: TrajectoryQuery, db: DB, actor: Investigator, request: Request):
    forms = normalize(body.plate)
    if not forms:
        raise HTTPException(422, "UNSUPPORTED_PLATE_FORMAT")
    body.plate = forms[0]
    result = s.trajectory(db, body)
    s.audit(
        db, actor, "trajectory.query", result["id"], str(body.run_id), request.state.correlation
    )
    db.commit()
    return output(result)


@app.get("/v1/trajectories/{query_id}", response_model=Result)
def journey(query_id: str, db: DB, actor: Investigator):
    row = db.get(m.Journey, query_id)
    if not row:
        raise HTTPException(404, "QUERY_NOT_FOUND")
    run = s.require_run(db, row.run_id)
    s.audit(db, actor, "trajectory.read", row.id, row.run_id)
    db.commit()
    return output({**s.serialize(row), "stale": row.version != run.version})


@app.get("/v1/analytics/{metric}", response_model=Result)
def metrics(metric: str, run_id: str, start: datetime, end: datetime, db: DB, actor: User):
    if metric not in ("summary", "counts", "od", "travel_times"):
        raise HTTPException(404, "METRIC_NOT_FOUND")
    result = analytics.summary(db, Window.model_validate(dict(run_id=run_id, start=start, end=end)))
    return output(result)


@app.get("/v1/watchlists", response_model=Result)
def watches(run_id: str, db: DB, actor: User):
    if actor not in ("administrator", "investigator", "approver"):
        raise HTTPException(403, "ROLE_DENIED")
    return output(
        [
            s.serialize(w)
            for w in db.scalars(select(m.Watchlist).where(m.Watchlist.run_id == run_id))
        ]
    )


@app.post("/v1/watchlists", response_model=Result)
def create_watch(body: WatchCreate, db: DB, actor: Investigator, key: Key):
    def action():
        s.require_run(db, str(body.run_id), lock=True)
        forms = normalize(body.plate)
        if not forms:
            raise HTTPException(422, "UNSUPPORTED_PLATE_FORMAT")
        row = m.Watchlist(
            **{**body.model_dump(), "run_id": str(body.run_id), "plate": forms[0]}, creator=actor
        )
        db.add(row)
        db.flush()
        s.audit(db, actor, "watchlist.created", row.id, row.run_id)
        return output(s.serialize(row))

    return recorded(db, actor, "watch.create", key, body.model_dump(mode="json"), action)


@app.post("/v1/watchlists/{watch_id}/{action}", response_model=Result)
def watch_action(watch_id: str, action: str, db: DB, actor: Approver, key: Key):
    def apply():
        watch = db.get(m.Watchlist, watch_id)
        if not watch:
            raise HTTPException(404, "WATCHLIST_NOT_FOUND")
        run = s.require_run(db, watch.run_id, lock=True)
        db.refresh(watch)
        if action == "approve" and watch.status == "draft" and watch.creator != actor:
            watch.status, watch.approver = "approved", actor
        elif action == "revoke" and watch.status == "approved":
            watch.status = "revoked"
        else:
            raise HTTPException(409, "INVALID_WATCHLIST_TRANSITION")
        db.add(m.Approval(watchlist_id=watch_id, actor=actor, action=action))
        s.audit(db, actor, "watchlist." + action, watch.id, watch.run_id)
        db.flush()
        s.match_watchlists(db, run)
        return output(s.serialize(watch))

    return recorded(db, actor, f"watch:{watch_id}", key, {"action": action}, apply)


@app.get("/v1/alerts", response_model=Result)
def alerts(run_id: str, db: DB, actor: Investigator, limit: int = Query(100, ge=1, le=200)):
    return output(
        [
            s.serialize(a)
            for a in db.scalars(
                select(m.Alert)
                .where(m.Alert.run_id == run_id)
                .order_by(m.Alert.created_at.desc())
                .limit(limit)
            )
        ]
    )


@app.post("/v1/alerts/{alert_id}/acknowledge", response_model=Result)
def acknowledge(alert_id: str, body: Decision, db: DB, actor: Investigator, key: Key):
    def action():
        alert = db.scalar(select(m.Alert).where(m.Alert.id == alert_id).with_for_update())
        if not alert:
            raise HTTPException(404, "ALERT_NOT_FOUND")
        alert.status = "acknowledged"
        db.add(m.AlertAction(alert_id=alert_id, actor=actor, **body.model_dump()))
        s.audit(db, actor, "alert.acknowledged", alert_id, alert.run_id, details=body.model_dump())
        return output(s.serialize(alert))

    return recorded(db, actor, f"ack:{alert_id}", key, body.model_dump(), action)


@app.post("/v1/observations/{observation_id}/reviews", response_model=Result)
def review(observation_id: str, body: Review, db: DB, actor: Investigator, key: Key):
    def action():
        obs = db.get(m.Observation, observation_id)
        if not obs:
            raise HTTPException(404, "OBSERVATION_NOT_FOUND")
        run = s.require_run(db, obs.run_id, lock=True)
        forms = normalize(body.plate or "")
        if body.status == "accepted" and not forms:
            raise HTTPException(422, "ACCEPTED_REVIEW_REQUIRES_SUPPORTED_PLATE")
        number = (
            db.scalar(
                select(func.max(m.Revision.number)).where(m.Revision.observation_id == obs.id)
            )
            or 0
        ) + 1
        revision = m.Revision(
            observation_id=obs.id,
            number=number,
            actor=actor,
            reason=body.reason,
            plate=forms[0] if forms else None,
            status=body.status,
        )
        db.add(revision)
        run.version += 1
        s.audit(db, actor, "observation.reviewed", obs.id, run.id, details=body.model_dump())
        # Prior alerts remain evidence-linked historical decisions, visibly requiring reassessment.
        for alert in db.scalars(select(m.Alert).where(m.Alert.observation_id == obs.id)):
            alert.status = "review_required"
            alert.details = {**alert.details, "observation_revised": True}
        db.flush()
        s.match_watchlists(db, run)
        return output(s.serialize(revision))

    return recorded(db, actor, f"review:{observation_id}", key, body.model_dump(), action)


@app.get("/v1/audit", response_model=Result)
def audits(run_id: str, db: DB, actor: Investigator, limit: int = Query(100, ge=1, le=200)):
    return output(
        [
            s.serialize(a)
            for a in db.scalars(
                select(m.Audit)
                .where(m.Audit.run_id == run_id)
                .order_by(m.Audit.created_at.desc())
                .limit(limit)
            )
        ]
    )


@app.get("/v1/jobs", response_model=Result)
def jobs(run_id: str, db: DB, actor: Admin):
    return output(
        [
            s.serialize(j)
            for j in db.scalars(
                select(m.Job).where(m.Job.run_id == run_id).order_by(m.Job.available_at).limit(200)
            )
        ]
    )
