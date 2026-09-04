"""Server-controlled registry and durable receipt. No decoding inside HTTP requests."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5

from fastapi import HTTPException
from pydantic import AwareDatetime, Field
from sqlalchemy import func, select

from roadeye import models as m
from roadeye import services as s
from roadeye.config import settings
from roadeye.contracts import Model
from roadeye.db import now
from roadeye.evidence import digest

REGISTRY = Path(__file__).resolve().parents[3] / "data/recorded_real/registry.json"


class VideoCreate(Model):
    recording_id: Literal["delhi_anpr"] = "delhi_anpr"
    duration_seconds: float = Field(default=60, gt=0, le=305)
    replay_anchor: AwareDatetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
    line_y: int = Field(default=300, ge=200, le=600)
    roi_top: int = Field(default=45, ge=40, le=150)


def registry() -> dict:
    return json.loads(REGISTRY.read_text())


def registered(identity: str) -> dict:
    if identity not in registry():
        raise HTTPException(404, "RECORDING_NOT_REGISTERED")
    return registry()[identity]


def enabled():
    if not settings.demo_enabled or not settings.recorded_enabled:
        raise HTTPException(404, "RECORDED_MODE_DISABLED")


def create(db, body: VideoCreate, actor: str) -> dict:
    enabled()
    recording = registered(body.recording_id)
    path = Path(recording["path"])
    if not path.is_file():
        raise HTTPException(409, "RECORDING_FILE_MISSING")
    if digest(path.read_bytes()) != recording["sha256"]:
        raise HTTPException(409, "RECORDING_DIGEST_MISMATCH")
    if body.duration_seconds > recording["duration_seconds"]:
        raise HTTPException(422, "WINDOW_EXCEEDS_RECORDING")
    try:
        from roadeye.recorded.inference import verify_models

        models = verify_models(settings.model_root)
    except (ImportError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
    dataset_id = f"recorded:{recording['sha256']}"
    if not db.get(m.Dataset, dataset_id):
        db.add(m.Dataset(id=dataset_id, manifest=recording))
    if not db.get(m.Camera, "REAL_C1"):
        db.add(
            m.Camera(
                id="REAL_C1",
                name="Recorded camera REAL_C1",
                zone_id=None,
                x=None,
                y=None,
                direction="uncalibrated",
            )
        )
        db.flush()
        db.add(m.Lane(id="REAL_C1-L1", camera_id="REAL_C1"))
    db.flush()
    anchor = body.replay_anchor.astimezone(timezone.utc)
    run = m.Run(
        dataset_id=dataset_id,
        scenario="recorded_video",
        source_mode="recorded_real",
        network="single-recorded-camera",
        state="received",
        clock=anchor,
        graph=[],
    )
    db.add(run)
    db.flush()
    config = {
        **body.model_dump(mode="json"),
        "replay_anchor": anchor.isoformat(),
        "anchor_meaning": "assigned replay anchor; actual capture date/time unknown",
        "manifest": recording,
        "models": models,
        "sample_fps": 5,
        "crop_encoding": "png",
        "policy": "recorded-onnx-v1",
        "timestamp_basis": "decoded PTS relative to stream start",
    }
    payload = {
        "kind": "recorded_video",
        "run_id": run.id,
        "config": config,
        "source_mode": "recorded_real",
        "inference_origin": "model_inference",
    }
    event = m.InputEvent(
        run_id=run.id,
        event_id=str(uuid5(UUID(run.id), "video")),
        actor=actor,
        key="recorded-video",
        digest=digest(json.dumps(payload, sort_keys=True).encode()),
        payload=payload,
    )
    db.add(event)
    db.flush()
    db.add(m.Job(id=event.id, run_id=run.id))
    db.flush()
    db.add(
        m.VideoTask(
            job_id=event.id,
            run_id=run.id,
            recording_id=body.recording_id,
            config=config,
            progress={"stage": "received", "frames_decoded": 0, "frames_processed": 0},
        )
    )
    s.audit(db, actor, "recording.received", event.id, run.id)
    return {"run_id": run.id, "state": "received", "source_mode": "recorded_real"}


def task_for(db, run_id: str):
    task = db.scalar(select(m.VideoTask).where(m.VideoTask.run_id == run_id))
    if not task:
        raise HTTPException(404, "RECORDED_RUN_NOT_FOUND")
    return task


def status(db, run_id: str) -> dict:
    task = task_for(db, run_id)
    job = db.get(m.Job, task.job_id)
    assert job
    counts = dict(
        db.execute(
            select(m.Job.state, func.count()).where(m.Job.run_id == run_id).group_by(m.Job.state)
        ).all()
    )
    outcomes = dict(
        db.execute(
            select(m.Observation.status, func.count())
            .where(m.Observation.run_id == run_id)
            .group_by(m.Observation.status)
        ).all()
    )
    passages = (
        db.scalar(select(func.count()).select_from(m.Passage).where(m.Passage.run_id == run_id))
        or 0
    )
    state = (
        "failed"
        if counts.get("poison")
        else "completed"
        if job.state == "done" and not (counts.get("pending") or counts.get("leased"))
        else "received"
        if job.attempts == 0
        else "processing"
    )
    return {
        "run_id": run_id,
        "recording_id": task.recording_id,
        "source_mode": "recorded_real",
        "inference_origin": "model_inference",
        "state": state,
        "attempts": job.attempts,
        "error": job.error,
        "config": task.config,
        "progress": task.progress,
        "jobs": counts,
        "vehicle_passages": passages,
        "outcomes": {k: outcomes.get(k, 0) for k in ("accepted", "review_required", "rejected")},
        "pending_outcomes": passages - sum(outcomes.values()),
        "accuracy": "unmeasured; independent human labels required",
        "count_rule": f"tracked bottom centre crosses y={task.config['line_y']} downward after at least two detections; 5 FPS IoU tracking",
        "limitations": "Single uncalibrated camera. Track IDs are local to this run. No routes, speed or congestion inferred.",
    }


def passages(db, run_id: str) -> list[dict]:
    task_for(db, run_id)
    result = []
    for passage in db.scalars(
        select(m.Passage)
        .where(m.Passage.run_id == run_id)
        .order_by(m.Passage.captured_at)
        .limit(1000)
    ):
        event = db.get(m.InputEvent, passage.input_id)
        observation = db.scalar(select(m.Observation).where(m.Observation.passage_id == passage.id))
        ocr = db.get(m.InputEvent, observation.input_id) if observation else None
        assert event
        result.append(
            {
                "id": passage.id,
                "track_id": passage.passage_key,
                "relative_seconds": event.payload["metadata"]["relative_seconds"],
                "assigned_timestamp": passage.captured_at.isoformat(),
                "original_frame_evidence_id": passage.evidence_id,
                "observation": s.serialize(observation) if observation else None,
                "inference": ocr.payload["metadata"] if ocr else None,
                "human_label": "",
                "human_readability": "unreviewed",
            }
        )
    return result


def retry(db, run_id: str, actor: str):
    task = task_for(db, run_id)
    run = s.require_run(db, run_id, lock=True)
    jobs = list(db.scalars(select(m.Job).where(m.Job.run_id == run_id).with_for_update()))
    if any(j.state == "leased" and j.lease_until and j.lease_until > now() for j in jobs):
        raise HTTPException(409, "WORKER_LEASE_ACTIVE")
    for job in jobs:
        if job.state == "poison" or job.id == task.job_id:
            job.state, job.attempts, job.available_at = "pending", 0, now()
            job.lease_until, job.lease_token, job.error = None, None, None
    run.state = "received"
    s.audit(db, actor, "recording.replayed", run_id, run_id)
    return {
        "run_id": run_id,
        "state": "received",
        "replay": "same run; stable events and evidence retained",
    }
