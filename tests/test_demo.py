"""Tests for the prediction-only local demo boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from roadeye.demo import DemoRepository, _bearing_degrees, create_app
from roadeye.s06_demo import S06_DISCLOSURE


def write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    app = create_app(fixture_config(tmp_path, monkeypatch))
    paths = [route.path for route in app.routes]
    assert "/api/status" in paths
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
