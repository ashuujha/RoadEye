"""Build a prediction-only plate index for a frozen RoadEye demo runtime."""

from __future__ import annotations

import argparse
import json
import logging
import random
import socket
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import easyocr
import numpy as np
import torch
from ultralytics import YOLO

from roadeye.demo import DemoRepository, ROOT
from roadeye.plate_search import PlateSearchIndex
from roadeye.runtime_ocr import (
    build_plate_index,
    canonical_sha256,
    collect_runtime_evidence,
    run_runtime_ocr,
)
from roadeye.tracklets import sha256, write_json

LOGGER = logging.getLogger(__name__)
ANPR_CONFIG = ROOT / "configs/anpr.json"
DETECTOR_TRAINING = ROOT / "reports/anpr-detector-training.json"
DETECTOR_SELECTION = ROOT / "reports/anpr-detector-selection.json"
OCR_MODELS = ROOT / "reports/anpr-models.json"
OCR_SELECTION = ROOT / "reports/anpr-ocr-selection.json"
SEALED_OCR_TEST = ROOT / "reports/anpr-ocr-test.json"
RUNTIME_MANIFEST_NAME = "plate-runtime-manifest.json"
PLATE_INDEX_NAME = "plate-index.json"
SEED = 20260909


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


@contextmanager
def network_blocked() -> Iterator[None]:
    """Fail closed if a runtime library attempts a network connection."""

    error = RuntimeError("Network access is forbidden during runtime OCR")
    with (
        patch.object(socket.socket, "connect", side_effect=error),
        patch.object(socket, "create_connection", side_effect=error),
        patch.object(urllib.request, "urlopen", side_effect=error),
    ):
        yield


def validate_frozen_inputs() -> dict[str, Any]:
    """Resolve and hash the frozen detector/OCR inputs without opening truth."""

    config = read_json(ANPR_CONFIG)
    detector_training = read_json(DETECTOR_TRAINING)
    detector_selection = read_json(DETECTOR_SELECTION)
    model_report = read_json(OCR_MODELS)
    ocr_selection = read_json(OCR_SELECTION)
    sealed_test = read_json(SEALED_OCR_TEST)
    if detector_training.get("status") != "PASS":
        raise ValueError("Detector training artifact is not accepted")
    if detector_selection.get("status") != "PASS":
        raise ValueError("Detector confidence selection is not frozen")
    if detector_selection.get("best_weights_sha256") != detector_training.get(
        "best_weights_sha256"
    ):
        raise ValueError("Detector report hashes disagree")
    detector_path = ROOT / detector_training["best_weights"]
    if sha256(detector_path) != detector_training["best_weights_sha256"]:
        raise ValueError("Detector weight hash mismatch")
    if ocr_selection.get("status") != "PASS":
        raise ValueError("OCR preprocessing selection is not frozen")
    if sealed_test.get("status") != "MEASURED":
        raise ValueError("Sealed OCR test report is missing")
    variant = ocr_selection["selected_variant"]
    if sealed_test.get("selected_variant") != variant:
        raise ValueError("Sealed OCR test used a different variant")

    frozen_sources = ocr_selection["frozen_sha256"]
    for relative in (
        "configs/anpr.json",
        "src/roadeye/anpr.py",
        "scripts/run_anpr.py",
    ):
        if sha256(ROOT / relative) != frozen_sources[relative]:
            raise ValueError(f"Frozen OCR source changed: {relative}")

    model_files: dict[str, str] = {}
    for name, record in model_report.get("models", {}).items():
        model_path = ROOT / config["model_directory"] / name
        if sha256(model_path) != record["sha256"]:
            raise ValueError(f"OCR model hash mismatch: {name}")
        model_files[model_path.relative_to(ROOT).as_posix()] = record["sha256"]
    if not model_files:
        raise ValueError("No frozen OCR recognition model is available")
    return {
        "config": config,
        "detector_path": detector_path,
        "detector_sha256": detector_training["best_weights_sha256"],
        "confidence_threshold": detector_selection[
            "selected_confidence_threshold"
        ],
        "variant": variant,
        "ocr_model_sha256": model_files,
        "anpr_config_sha256": sha256(ANPR_CONFIG),
        "ocr_selection_report_sha256": sha256(OCR_SELECTION),
        "sealed_ocr_test_report_sha256": sha256(SEALED_OCR_TEST),
    }


def build(config_path: Path) -> dict[str, Any]:
    frozen = validate_frozen_inputs()
    repository = DemoRepository(config_path)
    evidence = collect_runtime_evidence(repository, multi_camera_only=True)
    if not evidence:
        raise ValueError("No multi-camera runtime evidence is available")

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True, warn_only=True)
    LOGGER.info(
        "runtime_ocr_start scenario=%s evidence=%d",
        repository.config["scenario"],
        len(evidence),
    )
    with network_blocked():
        detector = YOLO(str(frozen["detector_path"]))
        reader = easyocr.Reader(
            frozen["config"]["ocr"]["languages"],
            gpu=False,
            model_storage_directory=str(
                ROOT / frozen["config"]["model_directory"]
            ),
            recog_network=frozen["config"]["ocr"]["recognition_network"],
            download_enabled=False,
            detector=False,
            recognizer=True,
            verbose=False,
        )
        entries, inference = run_runtime_ocr(
            evidence,
            detector=detector,
            reader=reader,
            image_size=frozen["config"]["detector"]["image_size"],
            confidence_threshold=frozen["confidence_threshold"],
            variant=frozen["variant"],
        )

    artifact_root = repository.paths.artifacts
    crop_inputs = [
        {
            "global_id": row.global_id,
            "visit_index": row.visit_index,
            "sample_index": row.sample_index,
            "crop_sha256": row.crop_sha256,
        }
        for row in evidence
    ]
    manifest = {
        "schema_version": 1,
        "build_status": "PASS",
        "prediction_status": "UNVERIFIED",
        "scope": "prediction_only_cityflow_runtime_plate_evidence",
        "scenario": repository.config["scenario"],
        "source": {
            "demo_config": config_path.resolve().relative_to(ROOT).as_posix(),
            "journeys_sha256": repository.run["prediction_sha256"]["journeys"],
            "input_crop_count": len(crop_inputs),
            "input_crop_set_sha256": canonical_sha256(crop_inputs),
            "sample_policy": "all_stored_samples_for_multi_camera_journeys",
        },
        "frozen_models": {
            "detector_weights_sha256": frozen["detector_sha256"],
            "ocr_model_sha256": frozen["ocr_model_sha256"],
        },
        "frozen_configuration": {
            "anpr_config_sha256": frozen["anpr_config_sha256"],
            "ocr_selection_report_sha256": frozen[
                "ocr_selection_report_sha256"
            ],
            "sealed_ocr_test_report_sha256": frozen[
                "sealed_ocr_test_report_sha256"
            ],
            "image_size": frozen["config"]["detector"]["image_size"],
            "detector_confidence_threshold": frozen["confidence_threshold"],
            "ocr_variant": frozen["variant"],
            "device": "cpu",
            "network_access": "blocked",
            "seed": SEED,
        },
        "implementation_sha256": {
            "src/roadeye/runtime_ocr.py": sha256(
                ROOT / "src/roadeye/runtime_ocr.py"
            ),
            "scripts/build_runtime_plate_index.py": sha256(Path(__file__)),
            "src/roadeye/anpr.py": sha256(ROOT / "src/roadeye/anpr.py"),
        },
        "results": inference,
        "entry_payload_sha256": canonical_sha256(entries),
        "claim_boundaries": {
            "benchmark_transcriptions_opened": False,
            "cityflow_identity_ground_truth_opened": False,
            "changes_vehicle_association": False,
            "ocr_score_is_probability": False,
            "predicted_text_is_ground_truth": False,
            "sealed_full_string_accuracy": read_json(SEALED_OCR_TEST)["metrics"][
                "full_string_accuracy"
            ],
        },
    }
    manifest_path = artifact_root / RUNTIME_MANIFEST_NAME
    write_json(manifest_path, manifest)
    manifest_sha256 = sha256(manifest_path)
    index = build_plate_index(
        scenario=repository.config["scenario"],
        journeys_sha256=repository.run["prediction_sha256"]["journeys"],
        selection_report_sha256=frozen["ocr_selection_report_sha256"],
        sealed_test_report_sha256=frozen["sealed_ocr_test_report_sha256"],
        runtime_manifest_sha256=manifest_sha256,
        entries=entries,
    )
    index_path = artifact_root / PLATE_INDEX_NAME
    write_json(index_path, index)
    index_sha256 = sha256(index_path)
    loaded = PlateSearchIndex.from_config(
        {
            "enabled": True,
            "availability": "READY",
            "index": PLATE_INDEX_NAME,
            "index_sha256": index_sha256,
        },
        artifact_root=artifact_root,
        journeys=repository.journeys,
        scenario=repository.config["scenario"],
        source_prediction_sha256=repository.run["prediction_sha256"]["journeys"],
    )
    if len(loaded.entries) != len(entries):
        raise RuntimeError("Generated plate index did not validate")
    return {
        "status": "PASS",
        "scenario": repository.config["scenario"],
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": manifest_sha256,
        "index": index_path.relative_to(ROOT).as_posix(),
        "index_sha256": index_sha256,
        "counts": inference["counts"],
        "timing_ms": inference["timing_ms"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Demo configuration whose frozen evidence will be indexed",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = build((ROOT / args.config).resolve() if not args.config.is_absolute() else args.config)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
