import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from roadeye import models as m
from roadeye.config import settings
from roadeye.contracts import Input, TrajectoryQuery
from roadeye.evidence import LocalEvidenceStore, digest
from roadeye.plates import consensus
from roadeye.trajectories import reconstruct, similar

DATA = Path(__file__).resolve().parents[2] / "data" / "synthetic"


def serialize(row) -> dict:
    return {
        c.name: (v.isoformat() if isinstance(v := getattr(row, c.name), datetime) else v)
        for c in row.__table__.columns
    }


def audit(
    db: Session,
    actor: str,
    operation: str,
    target: str,
    run_id: str | None = None,
    correlation: str = "worker",
    details: dict | None = None,
):
    db.add(
        m.Audit(
            actor=actor,
            operation=operation,
            target=target,
            run_id=run_id,
            correlation_id=correlation,
            details=details or {},
        )
    )


def require_run(db: Session, run_id: str, lock: bool = False) -> m.Run:
    query = select(m.Run).where(m.Run.id == run_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise HTTPException(404, "RUN_NOT_FOUND")
    return row


def seed(db: Session):
    if db.get(m.Dataset, "synthetic-v1"):
        return
    manifest = json.loads((DATA / "manifest.json").read_text())
    db.add(m.Dataset(id="synthetic-v1", manifest=manifest))
    for i in range(1, 4):
        db.add(m.Zone(id=f"Z{i}", name=f"Fictional zone {i}"))
    db.flush()
    for camera in json.loads((DATA / "cameras.json").read_text()):
        db.add(m.Camera(**camera))
    db.flush()
    for i in range(1, 7):
        db.add(m.Lane(id=f"C{i}-L1", camera_id=f"C{i}"))
    for edge in json.loads((DATA / "graph.json").read_text()):
        db.add(m.Edge(**edge))
    db.flush()


def scenario_events(scenario: str) -> list[dict]:
    # Select through manifest; user strings never become arbitrary paths.
    manifest = json.loads((DATA / "manifest.json").read_text())
    if scenario not in manifest["scenarios"]:
        raise HTTPException(422, "UNKNOWN_SCENARIO")
    path = DATA / "scenarios" / f"{scenario}.json"
    content = path.read_bytes()
    if digest(content) != manifest["files"][f"scenarios/{scenario}.json"]:
        raise HTTPException(409, "DATASET_DIGEST_MISMATCH")
    return json.loads(content)


def create_run(db: Session, scenario: str) -> m.Run:
    events = scenario_events(scenario)
    seed(db)
    run = m.Run(
        dataset_id="synthetic-v1",
        scenario=scenario,
        clock=min(datetime.fromisoformat(e["captured_at"]) for e in events),
        graph=[serialize(e) for e in db.scalars(select(m.Edge))],
    )
    db.add(run)
    db.flush()
    return run


def ingest(db: Session, item: Input, actor: str, key: str, correlation: str) -> dict:
    run = require_run(db, str(item.run_id), lock=True)
    body = item.model_dump(mode="json")
    fingerprint = digest(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
    old = db.scalar(
        select(m.InputEvent).where(
            m.InputEvent.run_id == run.id,
            ((m.InputEvent.actor == actor) & (m.InputEvent.key == key))
            | (m.InputEvent.event_id == str(item.event_id)),
        )
    )
    if old:
        if old.digest != fingerprint:
            raise HTTPException(409, "IDEMPOTENCY_PAYLOAD_CONFLICT")
        return {"input_id": old.id, "state": "durably_received", "duplicate": True}
    if not db.get(m.Camera, item.camera_id):
        raise HTTPException(422, "UNKNOWN_CAMERA")
    LocalEvidenceStore(settings.evidence_root).read(item.evidence_key)
    # OCR/passages are immutable contracts per camera-local passage.
    existing = db.scalars(select(m.InputEvent).where(m.InputEvent.run_id == run.id))
    for prior in existing:
        p = prior.payload
        if (
            item.kind == p["kind"]
            and item.kind != "heartbeat"
            and p["camera_id"] == item.camera_id
            and p["passage_id"] == item.passage_id
        ):
            raise HTTPException(409, "PASSAGE_INPUT_ALREADY_EXISTS_USE_ORIGINAL_EVENT_ID")
    row = m.InputEvent(
        run_id=run.id,
        event_id=str(item.event_id),
        actor=actor,
        key=key,
        digest=fingerprint,
        payload=body,
    )
    db.add(row)
    db.flush()
    db.add(m.Job(id=row.id, run_id=run.id))
    audit(db, actor, "input.received", row.id, run.id, correlation)
    return {"input_id": row.id, "state": "durably_received", "duplicate": False}


def emit_next(db: Session, run: m.Run, count: int = 1) -> int:
    events = scenario_events(run.scenario)
    emitted = 0
    while emitted < count and run.cursor < len(events):
        payload = {**events[run.cursor], "run_id": run.id}
        ingest(
            db,
            Input.model_validate(payload),
            "administrator",
            f"event:{payload['event_id']}",
            "replay",
        )
        run.clock = max(run.clock, datetime.fromisoformat(payload["captured_at"]))
        run.cursor += 1
        emitted += 1
    if run.cursor == len(events):
        run.state = "completed"
    return emitted


def observation_rows(
    db: Session, run_id: str, start: datetime, end: datetime, include_review: bool = True
) -> list[dict]:
    result = []
    pairs = db.execute(
        select(m.Observation, m.Passage)
        .join(m.Passage, m.Observation.passage_id == m.Passage.id)
        .where(
            m.Observation.run_id == run_id,
            m.Observation.captured_at >= start,
            m.Observation.captured_at < end,
        )
        .order_by(m.Observation.captured_at, m.Observation.id)
        .limit(1001)
    ).all()
    if len(pairs) > 1000:
        raise HTTPException(422, "WINDOW_TOO_DENSE_NARROW_TIME_RANGE")
    for obs, passage in pairs:
        revision = db.scalar(
            select(m.Revision)
            .where(m.Revision.observation_id == obs.id)
            .order_by(m.Revision.number.desc())
            .limit(1)
        )
        status = revision.status if revision else obs.status
        if not include_review and status != "accepted":
            continue
        result.append(
            {
                **serialize(obs),
                "plate": revision.plate if revision else obs.plate,
                "status": status,
                "score": obs.machine["score"],
                "camera_id": passage.camera_id,
                "lane_id": passage.lane_id,
                "evidence_id": passage.evidence_id,
                "revision": serialize(revision) if revision else None,
                "observed": True,
            }
        )
    return result


def health(db: Session, run: m.Run) -> list[dict]:
    rows = []
    for camera in db.scalars(select(m.Camera).order_by(m.Camera.id)):
        heartbeat = db.get(m.CameraHealth, (run.id, camera.id))
        age = (run.clock - heartbeat.last_seen).total_seconds() if heartbeat else None
        rows.append(
            {
                "camera_id": camera.id,
                "state": "stale" if age is None or age > 120 else "fresh",
                "last_heartbeat": heartbeat.last_seen.isoformat() if heartbeat else None,
                "age_seconds": age,
                "clock": run.clock.isoformat(),
                "basis": "synthetic event clock",
            }
        )
    return rows


def trajectory(db: Session, query: TrajectoryQuery, save: bool = True) -> dict:
    run = require_run(db, str(query.run_id), lock=True)
    all_nodes = observation_rows(db, run.id, query.start, query.end, query.include_review)
    nodes = [n for n in all_nodes if n["plate"] and similar(n["plate"], query.plate)]
    truncated = len(nodes) > query.limit
    nodes = nodes[: query.limit]
    result = reconstruct(nodes, run.graph, query.plate)
    result.update(
        {
            "run_id": run.id,
            "source_mode": run.source_mode,
            "result_version": run.version,
            "window_start": query.start.isoformat(),
            "window_end": query.end.isoformat(),
            "missing_coverage": [h for h in health(db, run) if h["state"] == "stale"],
            "truncated": truncated,
        }
    )
    if save:
        row = m.Journey(
            run_id=run.id, version=run.version, query=query.model_dump(mode="json"), result=result
        )
        db.add(row)
        db.flush()
        result = {**result, "id": row.id}
    return result


def add_alert(
    db: Session,
    run_id: str,
    key: str,
    kind: str,
    status: str,
    details: dict,
    observation_id: str | None = None,
    evidence_id: str | None = None,
):
    if not db.scalar(select(m.Alert).where(m.Alert.suppression_key == key)):
        alert = m.Alert(
            run_id=run_id,
            suppression_key=key,
            kind=kind,
            status=status,
            details=details,
            observation_id=observation_id,
            evidence_id=evidence_id,
        )
        db.add(alert)
        db.flush()
        audit(db, "worker", "alert.created", alert.id, run_id)


def match_watchlists(db: Session, run: m.Run):
    nodes = observation_rows(
        db,
        run.id,
        datetime(2000, 1, 1, tzinfo=run.clock.tzinfo),
        datetime(2100, 1, 1, tzinfo=run.clock.tzinfo),
    )
    for watch in db.scalars(
        select(m.Watchlist).where(m.Watchlist.run_id == run.id, m.Watchlist.status == "approved")
    ):
        for node in nodes:
            at = datetime.fromisoformat(node["captured_at"])
            if (
                not watch.valid_from <= at < watch.valid_until
                or not node["plate"]
                or node["status"] == "rejected"
            ):
                continue
            exact = node["plate"] == watch.plate and node["status"] == "accepted"
            if exact or similar(node["plate"], watch.plate):
                add_alert(
                    db,
                    run.id,
                    f"watch:{watch.id}:{node['id']}",
                    "watchlist_match",
                    "active" if exact else "review_required",
                    {
                        "watchlist_id": watch.id,
                        "reason": watch.reason,
                        "severity": watch.severity,
                        "match": "exact" if exact else "weak",
                    },
                    node["id"],
                    node["evidence_id"],
                )


def anomalies(db: Session, run: m.Run):
    nodes = observation_rows(
        db,
        run.id,
        datetime(2000, 1, 1, tzinfo=run.clock.tzinfo),
        datetime(2100, 1, 1, tzinfo=run.clock.tzinfo),
        False,
    )
    for plate in sorted({n["plate"] for n in nodes if n["plate"]}):
        result = reconstruct([n for n in nodes if n["plate"] == plate], run.graph, plate)
        by_id = {n["id"]: n for n in nodes}
        for link in result["rejected_links"] + result["review_candidates"]:
            if link.get("reason") in (
                "IMPOSSIBLE_TRAVEL",
                "SAME_PLATE_COLLISION",
                "REPEATED_CAMERA_LOOP",
            ):
                node = by_id[link["to"]]
                add_alert(
                    db,
                    run.id,
                    f"rule:{link['reason']}:{link['from']}:{link['to']}",
                    link["reason"],
                    "review_required",
                    {**link, "label": "rule-based indicator"},
                    node["id"],
                    node["evidence_id"],
                )
    # Only emit stale events once the scenario's inputs have been delivered/processed.
    if run.state == "completed" and not db.scalar(
        select(m.Job.id).where(m.Job.run_id == run.id, m.Job.state != "done")
    ):
        for camera in health(db, run):
            if camera["state"] == "stale":
                add_alert(
                    db,
                    run.id,
                    f"stale:{run.id}:{camera['camera_id']}",
                    "CAMERA_STALE",
                    "review_required",
                    camera,
                )


def process_input(db: Session, event: m.InputEvent):
    item = Input.model_validate(event.payload)
    run = require_run(db, event.run_id, lock=True)
    run.clock = max(run.clock, item.captured_at)
    if item.kind == "heartbeat":
        row = db.get(m.CameraHealth, (run.id, item.camera_id))
        if row:
            row.last_seen = max(row.last_seen, item.captured_at)
        else:
            db.add(
                m.CameraHealth(run_id=run.id, camera_id=item.camera_id, last_seen=item.captured_at)
            )
        run.version += 1
        return
    passage = db.scalar(
        select(m.Passage).where(
            m.Passage.run_id == run.id,
            m.Passage.camera_id == item.camera_id,
            m.Passage.passage_key == item.passage_id,
        )
    )
    if item.kind == "passage":
        if passage:
            return
        evidence = db.scalar(
            select(m.Evidence).where(
                m.Evidence.run_id == run.id, m.Evidence.object_key == item.evidence_key
            )
        )
        if not evidence:
            content = LocalEvidenceStore(settings.evidence_root).read(item.evidence_key)
            evidence = m.Evidence(
                run_id=run.id,
                object_key=item.evidence_key,
                digest=digest(content),
                size=len(content),
                media_type="image/svg+xml",
            )
            db.add(evidence)
            db.flush()
        db.add(
            m.Passage(
                run_id=run.id,
                passage_key=item.passage_id,
                camera_id=item.camera_id,
                lane_id=item.lane_id,
                captured_at=item.captured_at,
                input_id=event.id,
                evidence_id=evidence.id,
            )
        )
    else:
        if not passage:
            raise ValueError("PASSAGE_NOT_PROCESSED_YET")
        if passage.captured_at != item.captured_at or passage.evidence_id is None:
            raise ValueError("OCR_PASSAGE_METADATA_MISMATCH")
        if db.scalar(select(m.Observation.id).where(m.Observation.passage_id == passage.id)):
            return
        decision = consensus(
            item.readings,
            item.quality,
            item.input_confidence,
            settings.accept_score,
            settings.accept_margin,
        )
        obs = m.Observation(
            passage_id=passage.id,
            input_id=event.id,
            run_id=run.id,
            plate=decision["plate"],
            status=decision["status"],
            machine=decision,
            policy=decision["policy"],
            captured_at=item.captured_at,
        )
        db.add(obs)
        db.flush()
        for frame in sorted({r.frame_id for r in item.readings}):
            db.add(
                m.OCRReading(
                    observation_id=obs.id,
                    frame_id=frame,
                    candidates=[c for c in decision["contributions"] if c["frame_id"] == frame],
                )
            )
    run.version += 1
    db.flush()
    match_watchlists(db, run)
    audit(db, "worker", "input.processed", event.id, run.id)
