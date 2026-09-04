"""Database/auth failure boundaries; actual inference is exercised by recorded_acceptance.py."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from roadeye import jobs
from roadeye import models as m
from roadeye import services as s
from roadeye.config import settings
from roadeye.contracts import Input
from roadeye.db import SessionLocal, now
from roadeye.recorded.service import status
from sqlalchemy import select

from apps.api.main import app


def video_fixture(db):
    s.seed(db)
    dataset = m.Dataset(
        id=f"recorded-test:{uuid4()}",
        manifest={"purpose": "missing-file failure test, no inference answers"},
    )
    db.add(dataset)
    db.flush()
    run = m.Run(
        dataset_id=dataset.id,
        scenario="recorded_video",
        source_mode="recorded_real",
        network="single-recorded-camera",
        state="received",
        clock=datetime(2026, 1, 1, tzinfo=timezone.utc),
        graph=[],
    )
    db.add(run)
    db.flush()
    event = m.InputEvent(
        run_id=run.id,
        event_id=str(uuid4()),
        actor="administrator",
        key="video",
        digest="contract-test",
        payload={"kind": "recorded_video"},
    )
    db.add(event)
    db.flush()
    db.add(m.Job(id=event.id, run_id=run.id))
    db.flush()
    db.add(
        m.VideoTask(
            job_id=event.id,
            run_id=run.id,
            recording_id="delhi_anpr",
            config={
                "line_y": 300,
                "models": {},
                "manifest": {"path": "/nonexistent/roadeye-contract-recording"},
            },
            progress={},
        )
    )
    return run.id, event.id


def test_recorded_receipt_survives_connection_restart_and_worker_failure(monkeypatch):
    monkeypatch.setattr(settings, "recorded_enabled", False)
    with SessionLocal.begin() as db:
        run_id, job_id = video_fixture(db)
    # New sessions observe the same durable task, never an in-memory queue.
    with SessionLocal() as db:
        assert status(db, run_id)["state"] == "received"
    first = jobs.claim()
    assert first and first[0] == job_id
    with SessionLocal() as db:
        assert db.get(m.Job, job_id).state == "leased"
    recovered = jobs.claim(now() + timedelta(seconds=settings.lease_seconds + 1))
    assert recovered and recovered[0] == job_id and recovered[1] != first[1]
    assert not jobs.handle(*first)  # Fenced stale worker cannot write.
    assert not jobs.handle(*recovered)  # No enabled adapter -> explicit retry, no mock.
    with SessionLocal.begin() as db:
        job = db.get(m.Job, job_id)
        assert job and job.state == "pending" and "RECORDED_MODE_DISABLED" in job.error
        job.state = "poison"  # Keep this deliberately failing fixture out of unrelated tests.
        assert not db.scalar(select(m.Passage).where(m.Passage.run_id == run_id))


def test_run_scope_and_server_authorization(monkeypatch):
    monkeypatch.setattr(settings, "recorded_enabled", True)
    with SessionLocal.begin() as db:
        run_id, job_id = video_fixture(db)
        db.flush()
        db.get(m.Job, job_id).state = "poison"
        payload = s.scenario_events("normal_journey")[0] | {"run_id": run_id}
        with pytest.raises(HTTPException) as conflict:
            s.ingest(db, Input.model_validate(payload), "administrator", "wrong-mode", "test")
        assert conflict.value.status_code == 409
    with TestClient(app, headers={"X-RoadEye": "console"}) as client:
        assert client.get(f"/v1/recorded/runs/{run_id}/passages").status_code == 401
        for actor in ("viewer", "approver"):
            assert (
                client.post(
                    "/v1/auth/login", json={"actor": actor, "password": settings.demo_password}
                ).status_code
                == 200
            )
            assert client.get("/v1/recordings").status_code == 403
            assert client.get(f"/v1/recorded/runs/{run_id}/passages").status_code == 403
            assert client.get("/v1/evidence/unknown").status_code == 403
        client.post(
            "/v1/auth/login", json={"actor": "administrator", "password": settings.demo_password}
        )
        assert (
            client.post(
                "/v1/recorded/runs",
                json={"recording_id": "../../etc/passwd"},
                headers={"Idempotency-Key": "path"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/v1/demo/runs/{run_id}/control",
                json={"action": "play"},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 409
        )
        assert (
            client.get(
                "/v1/analytics/summary",
                params={
                    "run_id": run_id,
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-01T01:00:00Z",
                },
            ).status_code
            == 422
        )
