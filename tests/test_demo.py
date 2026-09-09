"""Tests for the prediction-only local demo boundary."""

from __future__ import annotations

import asyncio
import hashlib
import json
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np
import pytest

from roadeye.auth import (
    COOKIE_NAME,
    DEMO_PASSWORD_ENV,
    SESSION_TTL_SECONDS,
    LocalAuthService,
)
from roadeye.demo import DemoRepository, _bearing_degrees, create_app
from roadeye.s06_demo import S06_DISCLOSURE


class DemoResponse:
    def __init__(self, messages: list[dict]) -> None:
        start = next(
            message
            for message in messages
            if message["type"] == "http.response.start"
        )
        self.status_code = start["status"]
        self.headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in start["headers"]
        }
        self.content = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> object:
        return json.loads(self.content)


class DemoClient:
    """Small dependency-free ASGI client for the local API contract tests."""

    def __init__(self, app, *, base_url: str = "http://testserver") -> None:
        self.app = app
        self.scheme = urlsplit(base_url).scheme
        self.cookies: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        return None

    def get(self, path: str) -> DemoResponse:
        return self.request("GET", path)

    def post(self, path: str, **kwargs) -> DemoResponse:
        payload = kwargs.get("json")
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        return self.request("POST", path, body=body)

    def request(
        self, method: str, target: str, *, body: bytes = b""
    ) -> DemoResponse:
        parsed = urlsplit(target)
        headers = [(b"host", b"testserver")]
        if body:
            headers.extend(
                [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ]
            )
        if self.cookies:
            cookie = "; ".join(
                f"{key}={value}" for key, value in self.cookies.items()
            )
            headers.append((b"cookie", cookie.encode("latin-1")))
        messages: list[dict] = []
        request_sent = False

        async def receive() -> dict:
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.sleep(0)
            return {"type": "http.disconnect"}

        async def send(message: dict) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": self.scheme,
            "path": parsed.path,
            "raw_path": parsed.path.encode("ascii"),
            "query_string": parsed.query.encode("ascii"),
            "root_path": "",
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 443 if self.scheme == "https" else 80),
        }
        asyncio.run(self.app(scope, receive, send))
        response = DemoResponse(messages)
        if "set-cookie" in response.headers:
            cookie = SimpleCookie()
            cookie.load(response.headers["set-cookie"])
            for key, morsel in cookie.items():
                if morsel["max-age"] == "0":
                    self.cookies.pop(key, None)
                else:
                    self.cookies[key] = morsel.value
        return response


def write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_manifest(
    *, scenario: str, journeys_sha256: str, entries: list[dict]
) -> dict:
    entry_hash = hashlib.sha256(
        json.dumps(
            entries, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "build_status": "PASS",
        "prediction_status": "UNVERIFIED",
        "scenario": scenario,
        "source": {"journeys_sha256": journeys_sha256},
        "results": {"counts": {"indexed_entries": len(entries)}},
        "entry_payload_sha256": entry_hash,
        "claim_boundaries": {
            "benchmark_transcriptions_opened": False,
            "cityflow_identity_ground_truth_opened": False,
            "changes_vehicle_association": False,
            "ocr_score_is_probability": False,
            "predicted_text_is_ground_truth": False,
        },
    }


def fixture_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from roadeye import demo

    monkeypatch.setattr(demo, "ROOT", tmp_path)
    artifacts = tmp_path / "artifacts" / "run"
    frontend = tmp_path / "test_frontend"
    dataset = tmp_path / "data"
    frontend.mkdir(parents=True)
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    crop = artifacts / "crops" / "a.jpg"
    crop.parent.mkdir(parents=True)
    image = np.full((18, 24, 3), 90, dtype=np.uint8)
    assert cv2.imwrite(str(crop), image)
    crop_hash = hashlib.sha256(crop.read_bytes()).hexdigest()

    video = dataset / "video.avi"
    video.parent.mkdir(parents=True)
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (24, 18))
    assert writer.isOpened()
    writer.write(image)
    writer.release()

    position_a = {"latitude": 42.5, "longitude": -90.7, "kind": "approximate"}
    position_b = {"latitude": 42.501, "longitude": -90.699, "kind": "approximate"}
    sample_a = {
        "key": "validation/S02/c1/1",
        "camera": "c1",
        "frame": 1,
        "time_s": 0.0,
        "bbox_xywh": [2, 2, 10, 10],
        "baseline_score": 0.8,
        "video": "video.avi",
        "crop": "crops/a.jpg",
        "crop_sha256": crop_hash,
        "clipped_xyxy": [2, 2, 12, 12],
        "score_kind": "baseline_track_score_not_calibrated_detection_confidence",
    }
    sample_b = {**sample_a, "key": "validation/S02/c2/2", "camera": "c2", "time_s": 2.0}
    journeys = [
        {
            "global_id": "roadeye_fixture",
            "camera_count": 2,
            "geometry_status": "observations_only_no_road_route_claim",
            "visits": [
                {
                    "tracklet_key": sample_a["key"],
                    "camera": "c1",
                    "first_observed_s": 0.0,
                    "identified_at_s": 0.0,
                    "last_observed_s": 1.0,
                    "reference_position": position_a,
                    "evidence_samples": [sample_a],
                },
                {
                    "tracklet_key": sample_b["key"],
                    "camera": "c2",
                    "first_observed_s": 2.0,
                    "identified_at_s": 2.0,
                    "last_observed_s": 3.0,
                    "reference_position": position_b,
                    "evidence_samples": [sample_b],
                },
            ],
        }
    ]
    links = [
        {
            "from_key": sample_a["key"],
            "to_key": sample_b["key"],
            "similarity": 0.87,
            "second_best_similarity": 0.81,
            "margin": 0.06,
            "distance_m": 100.0,
            "temporal_gap_s": 1.0,
            "reason": "forward_time_and_distance_bound",
            "decision_time_s": 2.0,
            "score_kind": "uncalibrated_cosine_similarity_not_probability",
        }
    ]
    tracklets = {sample_a["key"]: {"samples": [sample_a]}, sample_b["key"]: {"samples": [sample_b]}}
    topology = {"kind": "approximate", "positions": {"c1": position_a, "c2": position_b}}
    journey_hash = write_json(artifacts / "journeys.json", journeys)
    links_hash = write_json(artifacts / "links.json", links)
    tracklet_hash = write_json(artifacts / "tracklets.json", tracklets)
    topology_hash = write_json(artifacts / "topology.json", topology)
    prepared_hash = write_json(
        artifacts / "prepared.json",
        {"artifact_sha256": {"tracklets.json": tracklet_hash, "topology.json": topology_hash}},
    )
    write_json(
        artifacts / "run.json",
        {
            "prepared_sha256": prepared_hash,
            "prediction_sha256": {"journeys": journey_hash, "links": links_hash},
        },
    )
    config = tmp_path / "configs" / "demo.json"
    write_json(
        config,
        {
            "schema_version": 1,
            "scope": "fixture_without_ground_truth",
            "scenario": "S02_fixture",
            "runtime_artifacts": "artifacts/run",
            "dataset_root": "data",
            "frontend_root": "test_frontend",
        },
    )
    return config


def test_catalog_search_and_evidence_labels(tmp_path, monkeypatch):
    repository = DemoRepository(fixture_config(tmp_path, monkeypatch))
    assert repository.status()["runtime_artifact_integrity"] == "PASS"
    assert repository.list_vehicles("c2")[0]["global_id"] == "roadeye_fixture"
    journey = repository.journey("roadeye_fixture")
    link = journey["visits"][1]["incoming_link"]
    assert link["appearance_similarity"] == 0.87
    assert link["is_probability"] is False
    assert link["verification_status"] == "not_scored_in_runtime"
    assert journey["visits"][1]["interpolation_from_previous"]["status"] == (
        "inferred_straight_line_not_observed_route"
    )


def test_crop_and_source_frame_are_exact_runtime_evidence(tmp_path, monkeypatch):
    repository = DemoRepository(fixture_config(tmp_path, monkeypatch))
    assert repository.crop_path("roadeye_fixture", 0, 0).name == "a.jpg"
    frame = repository.source_frame_jpeg("roadeye_fixture", 0, 0)
    decoded = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (18, 24)
    assert decoded[2, 2, 1] > decoded[2, 2, 0]


def test_changed_prediction_fails_before_catalog_load(tmp_path, monkeypatch):
    config = fixture_config(tmp_path, monkeypatch)
    journeys = tmp_path / "artifacts" / "run" / "journeys.json"
    journeys.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        DemoRepository(config)


def test_missing_crop_is_reported(tmp_path, monkeypatch):
    repository = DemoRepository(fixture_config(tmp_path, monkeypatch))
    repository.crop_path("roadeye_fixture", 0, 0).unlink()
    with pytest.raises(FileNotFoundError, match="missing or changed"):
        repository.crop_path("roadeye_fixture", 0, 0)


def test_paths_cannot_escape_the_project(tmp_path, monkeypatch):
    config = fixture_config(tmp_path, monkeypatch)
    value = json.loads(config.read_text())
    value["runtime_artifacts"] = "../outside"
    config.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="escapes"):
        DemoRepository(config)


def test_app_exposes_api_before_static_frontend(tmp_path, monkeypatch):
    monkeypatch.setenv(DEMO_PASSWORD_ENV, "x" * 16)
    app = create_app(fixture_config(tmp_path, monkeypatch))
    paths = [route.path for route in app.routes]
    assert "/api/status" in paths
    assert "/api/analytics" in paths
    assert "/api/plate-search/status" in paths
    assert "/api/plate-search" in paths
    assert paths.index("/api/status") < paths.index("")
    assert not any("evaluation" in route.path or "ground" in route.path for route in app.routes)


def test_s06_demo_requires_and_propagates_unverified_disclosure(tmp_path, monkeypatch):
    config = fixture_config(tmp_path, monkeypatch)
    value = json.loads(config.read_text())
    value["scenario"] = "S06_fixture"
    config.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="missing its disclosure"):
        DemoRepository(config)

    value["claim_status"] = "UNVERIFIED"
    value["disclosure"] = S06_DISCLOSURE
    config.write_text(json.dumps(value), encoding="utf-8")
    repository = DemoRepository(config)
    assert repository.status()["status"] == "UNVERIFIED"
    assert repository.status()["disclosure"] == S06_DISCLOSURE
    assert repository.list_vehicles()[0]["disclosure"] == S06_DISCLOSURE
    assert repository.journey("roadeye_fixture")["disclosure"] == S06_DISCLOSURE


def test_bearing_is_explicitly_derived_from_points():
    east = _bearing_degrees(
        {"latitude": 0.0, "longitude": 0.0},
        {"latitude": 0.0, "longitude": 1.0},
    )
    assert east == pytest.approx(90.0)


def test_demo_analytics_are_prediction_only(tmp_path, monkeypatch):
    repository = DemoRepository(fixture_config(tmp_path, monkeypatch))
    report = repository.analytics()
    assert report["status"] == "UNVERIFIED"
    assert report["summary"]["observed_runtime_visits"] == 2
    assert report["origin_destination_pairs"][0]["predicted_vehicle_count"] == 1
    assert report["claim_boundaries"]["uses_runtime_ground_truth"] is False


def test_demo_plate_search_is_explicitly_blocked_without_ocr_index(tmp_path, monkeypatch):
    repository = DemoRepository(fixture_config(tmp_path, monkeypatch))
    status = repository.plate_search_status()
    assert status["status"] == "UNVERIFIED"
    assert status["availability"] == "BLOCKED_PENDING_SEALED_OCR"
    assert repository.status()["plate_search"] == status
    assert repository.search_plates("KA01")["results"] == []


def test_demo_loads_only_prediction_linked_plate_entries(tmp_path, monkeypatch):
    config = fixture_config(tmp_path, monkeypatch)
    artifacts = tmp_path / "artifacts" / "run"
    runtime = json.loads((artifacts / "run.json").read_text(encoding="utf-8"))
    journeys = json.loads((artifacts / "journeys.json").read_text(encoding="utf-8"))
    sample = journeys[0]["visits"][0]["evidence_samples"][0]
    plate_index = {
        "schema_version": 1,
        "source": {
            "scenario": "S02_fixture",
            "journeys_sha256": runtime["prediction_sha256"]["journeys"],
        },
        "ocr_provenance": {
            "ocr_selection_report_sha256": "a" * 64,
            "sealed_ocr_test_report_sha256": "b" * 64,
            "runtime_ocr_manifest_sha256": "c" * 64,
        },
        "entries": [
            {
                "global_id": "roadeye_fixture",
                "visit_index": 0,
                "sample_index": 0,
                "tracklet_key": "validation/S02/c1/1",
                "camera": "c1",
                "observed_s": 0.0,
                "crop_sha256": sample["crop_sha256"],
                "predicted_plate_text": "KA01AB1234",
                "ocr_score": 0.82,
            }
        ],
    }
    manifest = runtime_manifest(
        scenario="S02_fixture",
        journeys_sha256=runtime["prediction_sha256"]["journeys"],
        entries=plate_index["entries"],
    )
    manifest_hash = write_json(
        artifacts / "plate-runtime-manifest.json", manifest
    )
    plate_index["ocr_provenance"][
        "runtime_ocr_manifest_sha256"
    ] = manifest_hash
    index_hash = write_json(artifacts / "plate-index.json", plate_index)
    value = json.loads(config.read_text(encoding="utf-8"))
    value["plate_search"] = {
        "enabled": True,
        "availability": "READY",
        "index": "plate-index.json",
        "index_sha256": index_hash,
        "manifest": "plate-runtime-manifest.json",
        "manifest_sha256": manifest_hash,
    }
    config.write_text(json.dumps(value), encoding="utf-8")

    repository = DemoRepository(config)
    result = repository.search_plates("ka-01-ab")
    assert result["availability"] == "READY"
    assert result["results"][0]["global_id"] == "roadeye_fixture"
    assert result["results"][0]["prediction_status"] == (
        "predicted_plate_text_not_ground_truth"
    )
    journey = repository.journey("roadeye_fixture")
    plate = journey["visits"][0]["evidence_samples"][0]["plate_prediction"]
    assert plate["predicted_plate_text"] == "KA01AB1234"
    assert plate["is_probability"] is False


def test_server_requires_a_long_environment_password(tmp_path, monkeypatch):
    config = fixture_config(tmp_path, monkeypatch)
    monkeypatch.delenv(DEMO_PASSWORD_ENV, raising=False)
    with pytest.raises(ValueError, match=f"{DEMO_PASSWORD_ENV} is required"):
        create_app(config)

    monkeypatch.setenv(DEMO_PASSWORD_ENV, "short")
    with pytest.raises(ValueError, match="at least 16 characters"):
        create_app(config)


def test_health_login_and_static_frontend_are_public_but_docs_are_disabled(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(DEMO_PASSWORD_ENV, "x" * 16)
    app = create_app(fixture_config(tmp_path, monkeypatch))
    with DemoClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ready"}
        assert client.get("/").text == "ok"
        assert client.get("/api/docs").status_code == 404
        response = client.post(
            "/api/auth/login",
            json={"actor": "administrator", "password": "wrong"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "INVALID_CREDENTIALS"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/auth/logout",
        "/api/status",
        "/api/vehicles",
        "/api/analytics",
        "/api/plate-search/status",
        "/api/plate-search?q=KA01",
        "/api/vehicles/roadeye_fixture",
        "/api/vehicles/roadeye_fixture/visits/0/samples/0/crop",
        "/api/vehicles/roadeye_fixture/visits/0/samples/0/frame",
    ],
)
def test_every_data_and_evidence_route_requires_a_session(
    path, tmp_path, monkeypatch
):
    monkeypatch.setenv(DEMO_PASSWORD_ENV, "x" * 16)
    app = create_app(fixture_config(tmp_path, monkeypatch))
    with DemoClient(app) as client:
        method = client.post if path == "/api/auth/logout" else client.get
        response = method(path)
    assert response.status_code == 401
    assert response.json() == {"detail": "SESSION_REQUIRED"}


def test_invalid_actor_retains_fastapi_validation_response(tmp_path, monkeypatch):
    monkeypatch.setenv(DEMO_PASSWORD_ENV, "x" * 16)
    app = create_app(fixture_config(tmp_path, monkeypatch))
    with DemoClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"actor": "operator", "password": "x" * 16},
        )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "literal_error"


def test_all_four_actors_have_identical_read_only_access(tmp_path, monkeypatch):
    password = "x" * 16
    monkeypatch.setenv(DEMO_PASSWORD_ENV, password)
    config = fixture_config(tmp_path, monkeypatch)
    app = create_app(config)
    expected_status = app.state.repository.status()

    for actor in ("viewer", "investigator", "administrator", "approver"):
        with DemoClient(app) as client:
            login = client.post(
                "/api/auth/login", json={"actor": actor, "password": password}
            )
            assert login.status_code == 200
            assert login.json() == {"actor": actor, "mode": "local_demo"}
            assert client.get("/api/auth/me").json() == login.json()
            assert client.get("/api/status").json() == expected_status
            assert client.post("/api/auth/logout").json() == {"logged_out": True}


def test_session_cookie_is_opaque_digest_only_and_https_aware(tmp_path, monkeypatch):
    password = "x" * 16
    monkeypatch.setenv(DEMO_PASSWORD_ENV, password)
    config = fixture_config(tmp_path, monkeypatch)
    app = create_app(config)

    with DemoClient(app, base_url="http://testserver") as client:
        response = client.post(
            "/api/auth/login",
            json={"actor": "administrator", "password": password},
        )
        cookie_header = response.headers["set-cookie"].lower()
        raw_token = client.cookies.get(COOKIE_NAME)
        assert "httponly" in cookie_header
        assert "samesite=strict" in cookie_header
        assert "path=/" in cookie_header
        assert f"max-age={SESSION_TTL_SECONDS}" in cookie_header
        assert "secure" not in cookie_header
        assert raw_token is not None
        assert raw_token not in app.state.auth_service._sessions
        assert all(
            len(digest) == 64
            and set(digest) <= set("0123456789abcdef")
            for digest in app.state.auth_service._sessions
        )

    secure_app = create_app(config)
    with DemoClient(secure_app, base_url="https://testserver") as client:
        response = client.post(
            "/api/auth/login",
            json={"actor": "viewer", "password": password},
        )
        assert "secure" in response.headers["set-cookie"].lower()


def test_session_restoration_expiry_and_logout(tmp_path, monkeypatch):
    clock = [1_000.0]
    authentication = LocalAuthService("x" * 16, now=lambda: clock[0])
    app = create_app(
        fixture_config(tmp_path, monkeypatch), auth_service=authentication
    )

    with DemoClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"actor": "investigator", "password": "x" * 16},
        )
        assert login.status_code == 200
        assert client.get("/api/auth/me").json() == {
            "actor": "investigator",
            "mode": "local_demo",
        }

        clock[0] += SESSION_TTL_SECONDS
        expired = client.get("/api/auth/me")
        assert expired.status_code == 401
        assert expired.json() == {"detail": "SESSION_REQUIRED"}
        assert authentication._sessions == {}

        client.cookies.clear()
        client.post(
            "/api/auth/login",
            json={"actor": "approver", "password": "x" * 16},
        )
        logout = client.post("/api/auth/logout")
        assert logout.json() == {"logged_out": True}
        assert "max-age=0" in logout.headers["set-cookie"].lower()
        assert client.get("/api/auth/me").status_code == 401


def test_authenticated_api_responses_preserve_prediction_semantics(
    tmp_path, monkeypatch
):
    password = "x" * 16
    monkeypatch.setenv(DEMO_PASSWORD_ENV, password)
    app = create_app(fixture_config(tmp_path, monkeypatch))
    repository = app.state.repository

    with DemoClient(app) as client:
        client.post(
            "/api/auth/login",
            json={"actor": "viewer", "password": password},
        )
        assert client.get("/api/status").json() == repository.status()
        assert client.get("/api/vehicles").json() == repository.list_vehicles()
        assert client.get("/api/analytics").json() == repository.analytics()
        assert (
            client.get("/api/plate-search/status").json()
            == repository.plate_search_status()
        )
        assert client.get("/api/vehicles/roadeye_fixture").json() == (
            repository.journey("roadeye_fixture")
        )
        crop = client.get(
            "/api/vehicles/roadeye_fixture/visits/0/samples/0/crop"
        )
        assert crop.status_code == 200
        assert crop.content == repository.crop_path(
            "roadeye_fixture", 0, 0
        ).read_bytes()
        frame = client.get(
            "/api/vehicles/roadeye_fixture/visits/0/samples/0/frame"
        )
        assert frame.status_code == 200
        assert frame.headers["content-type"] == "image/jpeg"


def test_frontend_contains_disabled_plate_search_contract():
    root = Path(__file__).resolve().parents[1]
    html = (root / "test_frontend" / "index.html").read_text(encoding="utf-8")
    javascript = (root / "test_frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="plate-search-input"' in html
    assert 'id="plate-search-button"' in html
    assert "/api/plate-search/status" in javascript
    assert "predicted plate observation" in javascript
