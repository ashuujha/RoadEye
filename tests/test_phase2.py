"""Behavior tests use synthetic observations, never demo assets."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import numpy as np
import pytest

from roadeye.association import associate, transition
from roadeye.evaluation import (
    association_metrics,
    box_iou,
    evaluate,
    group_quality,
    match_tracks,
)
from roadeye.phase2 import configuration
from roadeye.tracklets import (
    Observation,
    Tracklet,
    checked_path,
    extract_crops,
    load_tracklets,
    sha256,
)

POLICY = {
    "min_similarity": 0.85,
    "margin": 0.03,
    "max_gap_s": 45.0,
    "max_camera_distance_m": 1500.0,
    "overlap_distance_m": 150.0,
    "max_speed_mps": 40.0,
    "clock_tolerance_s": 2.0,
    "position_tolerance_m": 100.0,
}
EVAL = {
    "iou_threshold": 0.5,
    "min_matched_observations": 3,
    "min_observation_coverage": 0.5,
    "min_identity_purity": 0.8,
}
POSITIONS = {
    "c1": {"latitude": 42.5, "longitude": -90.7},
    "c2": {"latitude": 42.5, "longitude": -90.699},
    "c3": {"latitude": 42.5, "longitude": -90.698},
}


def obs(
    cam: str,
    lid: int,
    timestamp: float,
    frame: int = 1,
    box: tuple = (0.0, 0.0, 10.0, 10.0),
    scenario: str = "S04",
) -> Observation:
    return Observation(f"train/{scenario}/{cam}/{lid}", cam, frame, timestamp, box, 1.0)


def inputs(rows: list[Observation], vectors: list[list[float]]) -> tuple[dict, dict]:
    metadata = {}
    features = {}
    for row, vector in zip(rows, vectors, strict=True):
        metadata[row.key] = {
            "key": row.key,
            "camera": row.camera,
            "ready_s": row.time_s,
            "samples": [{"time_s": row.time_s, "frame": row.frame}],
        }
        features[row.key] = np.array(vector, dtype=np.float32)
    return metadata, features


def test_independent_ids_and_link_evidence():
    a, b = obs("c1", 7, 0), obs("c2", 900, 3)
    meta, vectors = inputs([a, b], [[1, 0], [1, 0]])
    result = associate([b, a], meta, vectors, POSITIONS, POLICY)
    assert result["assignments"][a.key] == result["assignments"][b.key]
    assert result["assignments"][a.key].startswith("roadeye_")
    link = result["links"][0]
    assert link["temporal_gap_s"] == 3
    assert link["from_evidence"]["frame"] == 1
    assert link["decision_time_s"] == 3
    assert link["score_kind"] == "uncalibrated_cosine_similarity_not_probability"


def test_appending_future_observations_does_not_rewrite_earlier_decisions():
    a, b, c = obs("c1", 1, 0), obs("c2", 2, 3), obs("c3", 3, 60)
    meta, vectors = inputs([a, b], [[1, 0], [1, 0]])
    before = associate([a, b], meta, vectors, POSITIONS, POLICY)
    meta2, vectors2 = inputs([a, b, c], [[1, 0], [1, 0], [0, 1]])
    # Extending source track until long after destination arrival used to affect links.
    after = associate(
        [a, b, obs("c1", 1, 50, 501), c], meta2, vectors2, POSITIONS, POLICY
    )
    assert after["decisions"][:2] == before["decisions"]
    assert after["links"] == before["links"]


def test_feature_prefix_is_unavailable_until_its_last_sample():
    a1, a2 = obs("c1", 1, 0), obs("c1", 1, 5, 51)
    b = obs("c2", 2, 3)
    meta, vectors = inputs([a2, b], [[1, 0], [1, 0]])
    result = associate([a1, a2, b], meta, vectors, POSITIONS, POLICY)
    assert result["decisions"][0]["key"] == b.key
    assert result["decisions"][0]["action"] == "new_identity"


def test_same_camera_cannot_merge_through_a_third_camera():
    rows = [obs("c1", 1, 0), obs("c2", 2, 3), obs("c1", 3, 6)]
    meta, vectors = inputs(rows, [[1, 0]] * 3)
    result = associate(rows, meta, vectors, POSITIONS, POLICY)
    assert result["assignments"][rows[2].key] != result["assignments"][rows[0].key]


def test_equal_appearance_candidates_abstain():
    rows = [obs("c1", 1, 0), obs("c1", 2, 1), obs("c2", 3, 3)]
    meta, vectors = inputs(rows, [[1, 0]] * 3)
    result = associate(rows, meta, vectors, POSITIONS, POLICY)
    assert not result["links"]
    assert result["decisions"][-1]["reason"] == "ambiguous_group_margin"


@pytest.mark.parametrize(
    "current,reason",
    [
        (obs("c2", 1, -1), "future_observation"),
        (obs("c2", 1, 46), "stale_observation"),
        (obs("c1", 2, 2), "same_camera"),
        (obs("c2", 1, 2, scenario="S01"), "different_partition_or_scenario"),
    ],
)
def test_transition_rejects_invalid_time_or_scope(current, reason):
    allowed, actual_reason, _ = transition(obs("c1", 1, 0), current, POSITIONS, POLICY)
    assert not allowed and actual_reason == reason


def test_topology_distance_and_travel_time():
    positions = {**POSITIONS, "far": {"latitude": 43, "longitude": -90}}
    assert (
        transition(obs("c1", 1, 0), obs("far", 2, 30), positions, POLICY)[1]
        == "outside_proximity_topology"
    )
    positions["c2"] = {"latitude": 42.5, "longitude": -90.69}
    assert (
        transition(obs("c1", 1, 0), obs("c2", 2, 1), positions, POLICY)[1]
        == "implausible_travel_time"
    )


def test_nearby_overlapping_views_are_allowed():
    assert transition(obs("c1", 1, 1), obs("c2", 1, 1), POSITIONS, POLICY)[0]


def test_zero_gt_coverage_produces_null_not_zero_accuracy():
    metrics = association_metrics(
        {}, {"a": "r1", "b": "r1"}, [{"from_key": "a", "to_key": "b"}]
    )
    assert metrics["status"] == "UNVERIFIED"
    assert metrics["link_precision_on_evaluable_links"] is None
    assert metrics["unscored_links"] == 1


def test_iou_uses_full_box_and_unique_frame_matching():
    rows = [
        obs("c1", lid, f, f, box=(1.0, 1.0, 10.0, 10.0))
        for f in range(1, 4)
        for lid in (1, 2)
    ]
    truth = {("c1", f): [("identity_a", [0.0, 0.0, 10.0, 10.0])] for f in range(1, 4)}
    mapping = match_tracks(rows, truth, EVAL)
    assert sum(m["matched_observations"] for m in mapping.values()) == 3
    assert sum(m["identity"] is not None for m in mapping.values()) == 1
    assert (
        box_iou(np.array([[0, 0, 10, 10]]), np.array([[0, 0, 100, 100]])).item() == 0.01
    )


def test_mixed_identity_track_is_ambiguous():
    rows = [obs("c1", 1, f, f) for f in range(1, 7)]
    truth = {("c1", f): [("a" if f <= 3 else "b", [0, 0, 10, 10])] for f in range(1, 7)}
    mapping = match_tracks(rows, truth, EVAL)
    assert mapping[rows[0].key]["identity"] is None
    assert mapping[rows[0].key]["status"] == "ambiguous"


def test_metrics_separate_correct_wrong_unknown_and_pairwise_recall():
    a, b, c, d = [f"train/S04/c{i}/1" for i in range(1, 5)]
    mapping = {a: {"identity": "x"}, b: {"identity": "x"}, c: {"identity": "y"}}
    assigned = dict.fromkeys([a, b, c, d], "group")
    links = [{"from_key": a, "to_key": k} for k in [b, c, d]]
    metrics = association_metrics(mapping, assigned, links)
    assert metrics["correct_links"] == 1 and metrics["incorrect_links"] == 1
    assert metrics["unscored_links"] == 1
    assert metrics["link_precision_on_evaluable_links"] == 0.5
    assert metrics["pairwise_global_id_precision"] == 1 / 3
    assert metrics["pairwise_global_id_recall"] == 1.0


def test_runtime_schema_has_no_identity_annotations():
    assert {field.name for field in fields(Observation)} == {
        "key",
        "camera",
        "frame",
        "time_s",
        "bbox_xywh",
        "baseline_score",
    }


def test_runtime_loader_never_opens_gt_and_loads_all_cameras(tmp_path, monkeypatch):
    cameras = []
    for cam in ["c1", "c2"]:
        path = tmp_path / cam / "mtsc" / "mtsc_fixture.txt"
        path.parent.mkdir(parents=True)
        path.write_text("1,1,0,0,10,10,1,-1,-1,-1\n")
        cameras.append(
            {
                "camera_id": cam,
                "baseline_tracks": str(path.relative_to(tmp_path)),
                "baseline_sha256": sha256(path),
                "fps_from_readme": 10,
                "offset_s": 0.0,
                "declared_frames": 1,
            }
        )
    window = {
        "start_s": 0.0,
        "end_s": 1.0,
        "partition": "train",
        "scenario": "S04",
        "cameras": cameras,
    }
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert "gt" not in path.parts
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    tracks, _ = load_tracklets(tmp_path, window)
    assert len(tracks) == 2 and {t.camera for t in tracks} == {"c1", "c2"}
    cameras[0]["baseline_sha256"] = "corrupt"
    with pytest.raises(ValueError, match="hash mismatch"):
        load_tracklets(tmp_path, window)
    cameras[0]["baseline_tracks"] = "c1/gt/gt.txt"
    with pytest.raises(ValueError, match="predicted MTSC"):
        load_tracklets(tmp_path, window)


def test_dataset_paths_cannot_escape_root(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        checked_path(tmp_path, "../gt/gt.txt")


def test_declared_development_and_evaluation_scenarios_do_not_overlap(tmp_path):
    config = json.loads(Path("configs/phase2.json").read_text())
    config["development_scenarios"].append("S04")
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="overlap"):
        configuration(path)


def test_crop_prefix_ignores_future_tail_and_clips_boxes(tmp_path):
    import cv2

    video = tmp_path / "sample.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 32))
    assert writer.isOpened()
    for _ in range(3):
        writer.write(np.full((32, 32, 3), 127, dtype=np.uint8))
    writer.release()
    rows = [
        obs("c1", 1, frame / 10, frame, box=(-3.0, -3.0, 50.0, 50.0))
        for frame in (1, 2, 3, 999)
    ]
    track = Tracklet(rows[0].key, "train", "S04", "c1", 1, rows)
    window = {
        "cameras": [{"camera_id": "c1", "video": "sample.avi", "fps_from_readme": 10}]
    }
    samples, failures = extract_crops(tmp_path, window, [track], tmp_path / "out", 3)
    assert not failures
    assert [s["frame"] for s in samples[track.key]] == [1, 2, 3]
    assert samples[track.key][0]["clipped_xyxy"] == [0, 0, 32, 32]


def test_nonfinite_embeddings_are_rejected():
    a = obs("c1", 1, 0)
    meta, features = inputs([a], [[float("nan"), 0]])
    with pytest.raises(ValueError, match="Invalid normalized embedding"):
        associate([a], meta, features, POSITIONS, POLICY)


def test_predicted_camera_coverage_is_not_automatically_verified():
    a, b, c = [f"train/S04/c{i}/1" for i in range(3)]
    mapping = {a: {"identity": "x"}, b: {"identity": "x"}}
    quality = group_quality(mapping, dict.fromkeys([a, b, c], "group"))
    assert quality["counts"] == {"partially_scored": 1}
    assert quality["max_fully_scored_consistent_camera_coverage"] == 0


def test_evaluator_rejects_changed_predictions_before_loading_labels(tmp_path):
    prepared = tmp_path / "prepared.json"
    prepared.write_text(json.dumps({"artifact_sha256": {}}))
    links = tmp_path / "links.json"
    links.write_text("[]")
    (tmp_path / "run.json").write_text(
        json.dumps(
            {
                "prepared_sha256": sha256(prepared),
                "prediction_sha256": {"links": sha256(links)},
            }
        )
    )
    links.write_text('[{"fabricated": true}]')
    with pytest.raises(ValueError, match="Predictions changed"):
        evaluate(tmp_path, tmp_path)
