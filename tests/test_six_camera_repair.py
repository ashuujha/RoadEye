from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from roadeye.calibration import (
    candidate_is_eligible,
    combine_development_metrics,
)
from roadeye.descriptor_fusion import (
    add_link_similarity_evidence,
    fuse_descriptors,
    tracklet_hsv_descriptors,
)
from roadeye.tracklets import sha256


def _metrics(correct: int, incorrect: int, pairs: tuple[int, int, int]) -> dict:
    predicted, true, correct_pairs = pairs
    return {
        "status": "MEASURED",
        "development_identities": 1,
        "mapped_development_tracklets": 2,
        "relevant_predicted_links": correct + incorrect,
        "evaluable_development_links": correct + incorrect,
        "correct_development_links": correct,
        "incorrect_development_links": incorrect,
        "unscored_development_links": 0,
        "ignored_links_without_development_endpoint": 0,
        "development_link_precision": correct / (correct + incorrect),
        "development_link_evaluation_coverage": 1.0,
        "predicted_development_cross_camera_pairs": predicted,
        "true_development_cross_camera_pairs": true,
        "correct_development_cross_camera_pairs": correct_pairs,
        "development_pairwise_precision": correct_pairs / predicted,
        "development_pairwise_recall": correct_pairs / true,
        "development_pairwise_f1": 0.0,
        "development_group_counts": {"fully_scored_consistent": 1},
        "max_fully_scored_consistent_development_camera_coverage": 2,
    }


def test_hsv_fusion_uses_hash_bound_prefix_crops_and_explains_score(
    tmp_path: Path,
) -> None:
    metadata = {}
    reid = {
        "a": np.array([1.0, 0.0], dtype=np.float32),
        "b": np.array([0.6, 0.8], dtype=np.float32),
    }
    for key, color in (("a", (0, 0, 255)), ("b", (0, 0, 240))):
        crop = tmp_path / "crops" / key / "000001.jpg"
        crop.parent.mkdir(parents=True)
        assert cv2.imwrite(str(crop), np.full((20, 30, 3), color, dtype=np.uint8))
        metadata[key] = {
            "samples": [
                {
                    "crop": crop.relative_to(tmp_path).as_posix(),
                    "crop_sha256": sha256(crop),
                }
            ]
        }
    hsv = tracklet_hsv_descriptors(tmp_path, metadata, (12, 4, 4))
    fused = fuse_descriptors(reid, hsv, 0.25)
    combined = float(np.dot(fused["a"], fused["b"]))
    assert combined == pytest.approx(0.75 * 0.6 + 0.25 * float(np.dot(hsv["a"], hsv["b"])))
    predictions = {
        "assignments": {"a": "roadeye_x", "b": "roadeye_x"},
        "links": [{"from_key": "a", "to_key": "b", "similarity": combined}],
        "decisions": [
            {
                "key": "b",
                "top_candidates": [{"from_key": "a", "similarity": combined}],
            }
        ],
        "journeys": [],
    }
    explained = add_link_similarity_evidence(
        predictions, reid, hsv, 0.25, "artifacts/source"
    )
    evidence = explained["links"][0]["appearance_evidence"]
    assert evidence["reconstructed_similarity"] == pytest.approx(combined)
    assert evidence["crop_artifact_root"] == "artifacts/source"
    assert "appearance_evidence" not in predictions["links"][0]


def test_fusion_rejects_tampered_crop(tmp_path: Path) -> None:
    crop = tmp_path / "crop.jpg"
    assert cv2.imwrite(str(crop), np.zeros((10, 10, 3), dtype=np.uint8))
    metadata = {"a": {"samples": [{"crop": "crop.jpg", "crop_sha256": "bad"}]}}
    with pytest.raises(ValueError, match="hash mismatch"):
        tracklet_hsv_descriptors(tmp_path, metadata, (12, 4, 4))


def test_combined_development_gate_requires_both_scenarios() -> None:
    by_scenario = {
        "S01": _metrics(7, 1, (7, 10, 7)),
        "S03": _metrics(1, 0, (1, 3, 1)),
    }
    combined = combine_development_metrics(by_scenario)
    assert combined["development_link_precision"] == pytest.approx(8 / 9)
    assert combined["development_pairwise_precision"] == pytest.approx(1.0)
    assert combined["development_pairwise_recall"] == pytest.approx(8 / 13)
    candidate = {
        "scenario_metrics": by_scenario,
        "combined_metrics": combined,
    }
    gate = {
        "minimum_evaluable_development_links": 8,
        "minimum_development_link_precision": 0.8,
        "minimum_evaluable_links_per_scenario": 1,
        "minimum_link_precision_per_scenario": 0.5,
    }
    assert candidate_is_eligible(candidate, gate)
    candidate["scenario_metrics"]["S03"] = {
        **candidate["scenario_metrics"]["S03"],
        "evaluable_development_links": 0,
        "development_link_precision": None,
    }
    assert not candidate_is_eligible(candidate, gate)
