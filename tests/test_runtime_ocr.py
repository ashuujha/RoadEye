"""Tests for prediction-only runtime OCR and index construction."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from roadeye.runtime_ocr import (
    RuntimeEvidence,
    build_plate_index,
    canonical_sha256,
    run_runtime_ocr,
    timing_summary,
)


class ArrayValue:
    def __init__(self, value):
        self.value = np.asarray(value)

    def cpu(self):
        return self

    def numpy(self):
        return self.value


class FakeDetector:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.results)


class FakeReader:
    def __init__(self, rows):
        self.rows = iter(rows)

    def recognize(self, *_args, **_kwargs):
        return next(self.rows)


def result(boxes, confidences, speed=10.0):
    return SimpleNamespace(
        boxes=SimpleNamespace(
            xyxy=ArrayValue(boxes),
            conf=ArrayValue(confidences),
        ),
        speed={"preprocess": 1.0, "inference": speed, "postprocess": 2.0},
    )


def evidence(path: Path, index: int) -> RuntimeEvidence:
    return RuntimeEvidence(
        global_id=f"roadeye_{index}",
        visit_index=0,
        sample_index=0,
        tracklet_key=f"S02/c{index}/{index}",
        camera=f"c{index}",
        observed_s=float(index),
        crop_sha256=str(index + 1) * 64,
        crop_path=path,
    )


def test_runtime_ocr_indexes_only_usable_predictions(tmp_path):
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    image = np.full((40, 80, 3), 128, dtype=np.uint8)
    assert cv2.imwrite(str(first), image)
    assert cv2.imwrite(str(second), image)
    detector = FakeDetector(
        [
            result([[4, 5, 70, 30], [2, 2, 20, 15]], [0.8, 0.9]),
            result([], []),
        ]
    )
    reader = FakeReader([[[None, "ka-01-ab-1234", 0.72]]])

    entries, report = run_runtime_ocr(
        [evidence(first, 0), evidence(second, 1)],
        detector=detector,
        reader=reader,
        image_size=640,
        confidence_threshold=0.5,
        variant="color_upscale",
    )

    assert entries[0]["predicted_plate_text"] == "KA01AB1234"
    assert entries[0]["ocr_score"] == 0.72
    assert report["counts"] == {
        "input_evidence": 2,
        "detector_boxes": 2,
        "ocr_attempts": 1,
        "indexed_entries": 1,
        "excluded": {
            "no_plate_box": 1,
            "unreadable_crop": 0,
            "invalid_plate_box": 0,
            "empty_or_short_ocr": 0,
        },
        "failures": 0,
    }
    assert detector.calls[0]["device"] == "cpu"
    assert detector.calls[0]["conf"] == 0.5


def test_runtime_ocr_excludes_short_recognition(tmp_path):
    path = tmp_path / "crop.jpg"
    assert cv2.imwrite(str(path), np.full((20, 50, 3), 200, dtype=np.uint8))
    detector = FakeDetector([result([[0, 0, 45, 18]], [0.95])])
    reader = FakeReader([[[None, "-A-", 0.4]]])

    entries, report = run_runtime_ocr(
        [evidence(path, 0)],
        detector=detector,
        reader=reader,
        image_size=640,
        confidence_threshold=0.5,
        variant="color_upscale",
    )

    assert entries == []
    assert report["counts"]["excluded"]["empty_or_short_ocr"] == 1


def test_plate_index_contains_provenance_but_no_truth_fields():
    index = build_plate_index(
        scenario="S02",
        journeys_sha256="a" * 64,
        selection_report_sha256="b" * 64,
        sealed_test_report_sha256="c" * 64,
        runtime_manifest_sha256="d" * 64,
        entries=[],
    )
    assert index["source"]["journeys_sha256"] == "a" * 64
    assert index["ocr_provenance"]["runtime_ocr_manifest_sha256"] == "d" * 64
    assert "transcription" not in str(index).lower()
    assert canonical_sha256(index) == canonical_sha256(index)


def test_empty_timing_summary_is_explicit():
    assert timing_summary([]) == {
        "samples": 0,
        "mean_ms": None,
        "p50_ms": None,
        "p95_ms": None,
        "max_ms": None,
    }
