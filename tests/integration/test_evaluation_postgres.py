from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from roadeye import models as m
from roadeye.config import settings
from roadeye.db import SessionLocal
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from apps.api.main import app
from tests.integration.test_recorded_postgres import video_fixture


def test_evaluation_is_authorized_append_only_idempotent_and_separate(monkeypatch):
    monkeypatch.setattr(settings, "recorded_enabled", True)
    with SessionLocal.begin() as db:
        run_id, job_id = video_fixture(db)
        db.flush()
        db.get(m.Job, job_id).state = "poison"
    route = f"/v1/recorded/runs/{run_id}/evaluation"
    body = {
        "kind": "missed_vehicle",
        "target_id": str(uuid4()),
        "relative_seconds": 4,
        "reviewer_name": "Test reviewer",
        "passage_assessment": "valid",
        "readability": "unreadable",
    }
    with TestClient(app, headers={"X-RoadEye": "console"}) as client:
        assert client.get(route).status_code == 401
        for actor in ("viewer", "investigator"):
            assert (
                client.post(
                    "/v1/auth/login", json={"actor": actor, "password": settings.demo_password}
                ).status_code
                == 200
            )
            if actor == "viewer":
                assert client.get(route).status_code == 403
                assert (
                    client.post(route, json=body, headers={"Idempotency-Key": "label"}).status_code
                    == 403
                )
                assert client.get("/v1/recordings/delhi_anpr/video").status_code == 403
        first = client.post(route, json=body, headers={"Idempotency-Key": "label"})
        assert first.status_code == 200, first.text
        assert (
            client.post(route, json=body, headers={"Idempotency-Key": "label"}).json()
            == first.json()
        )
        assert (
            client.post(
                route, json=body | {"notes": "changed"}, headers={"Idempotency-Key": "label"}
            ).status_code
            == 409
        )
        revised = client.post(
            route,
            json=body | {"notes": "independent revision"},
            headers={"Idempotency-Key": "label-2"},
        )
        assert revised.status_code == 200
        assert revised.json()["data"]["revision"] == 2
        result = client.get(route).json()["data"]
        assert len(result["labels"]) == 1
        assert result["metrics"]["ground_truth_vehicle_passages"] is None
        assert (
            client.post(
                route, json=body | {"relative_seconds": 60}, headers={"Idempotency-Key": "outside"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                route,
                json=body | {"kind": "passage", "passage_id": str(uuid4())},
                headers={"Idempotency-Key": "wrong-run"},
            ).status_code
            == 409
        )
    with SessionLocal() as db:
        assert (
            len(
                list(
                    db.scalars(select(m.EvaluationLabel).where(m.EvaluationLabel.run_id == run_id))
                )
            )
            == 2
        )
        assert not db.scalar(select(m.Observation).where(m.Observation.run_id == run_id))
    with pytest.raises(DBAPIError), SessionLocal.begin() as db:
        db.execute(
            text("UPDATE evaluation_labels SET reviewer_name='overwritten' WHERE run_id=:run"),
            {"run": run_id},
        )


def test_registered_source_supports_authorized_range(monkeypatch, tmp_path):
    from roadeye.evidence import digest
    from roadeye.recorded import service

    monkeypatch.setattr(settings, "recorded_enabled", True)
    content = b"test-range-bytes-not-video-inference"
    path = tmp_path / "source.mp4"
    path.write_bytes(content)
    monkeypatch.setattr(
        service, "registered", lambda identity: {"path": str(path), "sha256": digest(content)}
    )
    with TestClient(app, headers={"X-RoadEye": "console"}) as client:
        route = "/v1/recordings/delhi_anpr/video"
        assert client.get(route).status_code == 401
        client.post(
            "/v1/auth/login", json={"actor": "investigator", "password": settings.demo_password}
        )
        response = client.get(route, headers={"Range": "bytes=0-3"})
        assert response.status_code == 206
        assert response.content == content[:4]
        assert response.headers["content-range"] == f"bytes 0-3/{len(content)}"
