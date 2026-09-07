"""Synthetic behavior checks for the bounded Re-ID experiment; no demo fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from roadeye.phase2 import configuration
from roadeye.tracklets import Observation, Tracklet, extract_crops


def test_quality_prefix_skips_bad_crops_spaces_samples_and_ignores_future(tmp_path):
    video = tmp_path / "synthetic.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 64))
    assert writer.isOpened()
    textured = np.random.default_rng(0).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    for index in range(6):
        writer.write(np.full_like(textured, 100) if index == 1 else textured)
    writer.release()
    times = [0.0, 0.1, 0.2, 0.3, 0.7, 1.2, 9.0]
    rows = [
        Observation(
            "train/S01/c1/7",
            "c1",
            i + 1 if i < 6 else 999,
            t,
            (0, 0, 8, 8) if i == 0 else (0, 0, 64, 64),
            1.0,
        )
        for i, t in enumerate(times)
    ]
    window = {
        "cameras": [
            {"camera_id": "c1", "video": "synthetic.avi", "fps_from_readme": 10}
        ]
    }
    quality = {
        "min_side_px": 24,
        "min_area_px": 2304,
        "min_laplacian_variance": 20,
        "max_wait_s": 3,
        "min_interval_s": 0.5,
    }
    track = Tracklet(rows[0].key, "train", "S01", "c1", 7, rows)
    samples, failures = extract_crops(
        tmp_path, window, [track], tmp_path / "full", 3, quality
    )
    assert not failures
    assert [s["frame"] for s in samples[track.key]] == [3, 5, 6]
    assert samples[track.key][-1]["time_s"] == 1.2
    assert all(
        s["crop_quality"]["laplacian_variance"] >= 20 for s in samples[track.key]
    )
    # Remove all future observations. The emitted prefix bytes must be identical.
    track.observations = rows[:6]
    prefix, _ = extract_crops(
        tmp_path, window, [track], tmp_path / "prefix", 3, quality
    )
    assert prefix == samples
    # A replay ending before the third eligible sample cannot emit an embedding.
    track.observations = rows[:5]
    incomplete, exclusions = extract_crops(
        tmp_path, window, [track], tmp_path / "early", 3, quality
    )
    assert not incomplete
    assert exclusions[-1]["reason"] == "incomplete_quality_prefix"


def test_development_role_is_explicit_and_partition_checked(tmp_path):
    config = json.loads(Path("configs/reid-dev-imagenet_prefix.json").read_text())
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    assert configuration(path)[0]["run_role"] == "development"
    config["run_role"] = "evaluation"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="declared evaluation"):
        configuration(path)
    config["run_role"] = "anything"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="Invalid run role"):
        configuration(path)


def test_vehicle_checkpoint_corruption_is_rejected_before_loading(tmp_path):
    from roadeye.vehicle_encoder import load_vehicle_encoder

    path = tmp_path / "bad.pth"
    path.write_bytes(b"not a trusted checkpoint")
    with pytest.raises(ValueError, match="checksum"):
        load_vehicle_encoder(path)


def test_quality_policy_cannot_wait_less_than_required_spacing(tmp_path):
    quality = {"max_wait_s": 0.5, "min_interval_s": 0.5}
    with pytest.raises(ValueError, match="quality prefix"):
        extract_crops(tmp_path, {"cameras": []}, [], tmp_path, 3, quality)


def test_unknown_model_cannot_trigger_a_download(tmp_path):
    from roadeye.embeddings import download_weights

    with pytest.raises(ValueError, match="Unsupported"):
        download_weights(tmp_path / "weights", "invented_vehicle_model")


def test_recall_counts_tracks_excluded_by_quality_filter():
    from roadeye.evaluation import association_metrics

    keys = [f"train/S01/c{i}/1" for i in range(3)]
    mapping = {key: {"identity": "vehicle"} for key in keys}
    assignments = {keys[0]: "roadeye_a", keys[1]: "roadeye_a"}
    metrics = association_metrics(
        mapping, assignments, [{"from_key": keys[0], "to_key": keys[1]}]
    )
    assert metrics["pairwise_global_id_recall"] == 1.0
    assert metrics["true_cross_camera_pairs_on_all_mappable_tracklets"] == 3
    assert metrics["pairwise_global_id_recall_all_mappable_tracklets"] == 1 / 3


def test_frozen_config_cannot_be_retuned_after_selection(tmp_path, monkeypatch):
    from roadeye import phase2
    from roadeye.tracklets import text_sha256, write_json

    monkeypatch.setattr(phase2, "ROOT", tmp_path)
    write_json(tmp_path / "window.json", {"scenario": "S05"})
    write_json(tmp_path / "configs/reid-experiment.json", {})
    write_json(tmp_path / "reports/reid-development.json", {})
    config = {
        "window": "window.json",
        "cityflow_training": False,
        "development_scenarios": ["S01"],
        "evaluation_scenarios": ["S05"],
        "selection_manifest": "selection.json",
        "association": {"min_similarity": 0.8},
    }
    config_path = tmp_path / "config.json"
    write_json(config_path, config)
    write_json(
        tmp_path / "selection.json",
        {
            "config_sha256": text_sha256(config_path),
            "evaluation_window_sha256": text_sha256(tmp_path / "window.json"),
            "protocol_sha256": text_sha256(tmp_path / "configs/reid-experiment.json"),
            "development_report_sha256": text_sha256(
                tmp_path / "reports/reid-development.json"
            ),
            "runtime_source_sha256": {},
        },
    )
    assert configuration(config_path)[1]["scenario"] == "S05"
    config_path.write_bytes(config_path.read_bytes().replace(b"\r\n", b"\n"))
    assert configuration(config_path)[1]["scenario"] == "S05"
    config["association"]["min_similarity"] = 0.7
    write_json(config_path, config)
    with pytest.raises(ValueError, match="Frozen experiment changed"):
        configuration(config_path)


def test_invalid_baseline_box_requires_explicit_exclusion_policy(tmp_path):
    from roadeye.tracklets import load_tracklets, sha256

    source = tmp_path / "c1/mtsc/mtsc_fixture.txt"
    source.parent.mkdir(parents=True)
    source.write_text("1,7,0,0,-2,10,1,-1,-1,-1\n2,7,0,0,10,10,1,-1,-1,-1\n")
    window = {
        "scenario": "S05",
        "partition": "validation",
        "start_s": 0,
        "end_s": 1,
        "cameras": [
            {
                "camera_id": "c1",
                "baseline_tracks": "c1/mtsc/mtsc_fixture.txt",
                "baseline_sha256": sha256(source),
                "fps_from_readme": 10,
                "offset_s": 0,
                "declared_frames": 2,
            }
        ],
    }
    with pytest.raises(ValueError, match="Invalid box"):
        load_tracklets(tmp_path, window)
    tracks, sources = load_tracklets(tmp_path, window, "exclude_nonpositive_and_record")
    assert len(tracks[0].observations) == 1
    assert tracks[0].observations[0].frame == 2
    rejected = sources["c1"]["excluded_nonpositive_boxes"]
    assert len(rejected) == 1 and rejected[0]["source_line"] == 1
    assert rejected[0]["inside_window"]
    assert sha256(source) == window["cameras"][0]["baseline_sha256"]
