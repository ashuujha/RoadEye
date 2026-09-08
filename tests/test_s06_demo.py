"""Tests for S06 prediction-only reporting and claim boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from roadeye.s06_demo import S06_DISCLOSURE, build_s06_report, markdown_report
from scripts.run_s06_demo import reject_ground_truth_and_evaluation_outputs


def _sample(camera: str, frame: int) -> dict:
    return {
        "key": f"test/S06/{camera}/{frame}",
        "camera": camera,
        "frame": frame,
        "time_s": float(frame),
        "bbox_xywh": [1.0, 2.0, 30.0, 40.0],
        "crop": f"crops/{camera}.jpg",
        "crop_sha256": "a" * 64,
        "video": f"AICity22_Track1_MTMC_Tracking/test/S06/{camera}/vdo.avi",
        "baseline_score": -1.0,
        "score_kind": "baseline_track_score_not_calibrated_detection_confidence",
    }


def test_s06_report_discloses_unverified_maximum_without_metrics():
    visits = []
    links = []
    for index, number in enumerate(range(41, 47), 1):
        camera = f"c0{number}"
        sample = _sample(camera, index)
        visits.append(
            {
                "tracklet_key": sample["key"],
                "camera": camera,
                "first_observed_s": float(index),
                "identified_at_s": float(index),
                "last_observed_s": float(index + 1),
                "reference_position": {
                    "latitude": 10.0 + index / 1000,
                    "longitude": 20.0,
                    "kind": "fixture",
                },
                "evidence_samples": [sample],
            }
        )
        if index > 1:
            links.append(
                {
                    "from_key": visits[-2]["tracklet_key"],
                    "to_key": sample["key"],
                    "similarity": 0.8 + index / 100,
                    "second_best_similarity": 0.7,
                    "margin": 0.1 + index / 100,
                    "temporal_gap_s": 1.0,
                    "distance_m": 100.0,
                    "reason": "forward_time_and_distance_bound",
                    "decision_time_s": float(index),
                    "score_kind": "uncalibrated_cosine_similarity_not_probability",
                }
            )
    journeys = [
        {
            "global_id": "roadeye_fixture",
            "camera_count": 6,
            "visits": visits,
            "geometry_status": "observations_only_no_road_route_claim",
        },
        {
            "global_id": "roadeye_single",
            "camera_count": 1,
            "visits": [visits[0]],
            "geometry_status": "observations_only_no_road_route_claim",
        },
    ]
    window = {
        "scenario": "S06",
        "partition": "test",
        "start_s": 0.0,
        "end_s": 199.9,
        "baseline_filename": "mtsc_tnt_mask_rcnn.txt",
        "selection_rule": "metadata_only",
        "disclosure": S06_DISCLOSURE,
        "cameras": [{"camera_id": f"c0{number}"} for number in range(41, 47)],
    }
    selection = {
        "status": "PASS",
        "selected_policy": {"min_similarity": 0.675},
        "selected_hsv_weight": 0.0,
    }
    run = {
        "baseline_tracklets": 7,
        "embedded_tracklets": 7,
        "predicted_links": 5,
        "global_ids": 2,
    }
    report = build_s06_report(
        journeys=journeys,
        links=links,
        run=run,
        prepared={"model": {"model": "fixture"}},
        window=window,
        selection=selection,
        selection_sha256="b" * 64,
    )
    assert report["status"] == "UNVERIFIED"
    assert report["disclosure"] == S06_DISCLOSURE
    assert report["accuracy_metrics"] is None
    assert report["verified_six_camera_criterion"] == {
        "status": "FAIL",
        "affected_by_this_run": False,
        "existing_max_fully_verified_consistent_camera_count": 2,
        "reason": "An unscored S06 prediction cannot change a verified criterion.",
    }
    assert report["prediction_summary"]["maximum_predicted_camera_span"] == 6
    assert report["prediction_summary"]["identities_at_maximum_span"] == 1
    assert report["prediction_summary"]["camera_span_distribution"] == {
        "1": 1,
        "6": 1,
    }
    assert all(
        visit["incoming_link"] is None
        or visit["incoming_link"]["is_probability"] is False
        for visit in report["maximum_span_predictions"][0]["visits"]
    )
    assert S06_DISCLOSURE in markdown_report(report)


def test_s06_report_rejects_an_incomplete_camera_window():
    window = {
        "scenario": "S06",
        "disclosure": S06_DISCLOSURE,
        "cameras": [{"camera_id": "c041"}],
    }
    try:
        build_s06_report(
            journeys=[],
            links=[],
            run={},
            prepared={},
            window=window,
            selection={"status": "PASS"},
            selection_sha256="x",
        )
    except ValueError as error:
        assert "all six" in str(error)
    else:
        raise AssertionError("Incomplete S06 window was accepted")


def test_s06_runtime_guard_rejects_gt_and_evaluation_paths(tmp_path: Path):
    allowed = tmp_path / "prediction.json"
    with reject_ground_truth_and_evaluation_outputs():
        allowed.write_text("prediction", encoding="utf-8")
        with pytest.raises(RuntimeError, match="prohibited access"):
            (tmp_path / "gt.txt").open("w", encoding="utf-8")
        evaluation = tmp_path / "evaluation" / "result.json"
        evaluation.parent.mkdir()
        with pytest.raises(RuntimeError, match="prohibited access"):
            evaluation.open("w", encoding="utf-8")
    assert allowed.read_text(encoding="utf-8") == "prediction"
