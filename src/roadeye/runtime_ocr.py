"""Offline runtime OCR over hash-verified RoadEye journey evidence."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

import cv2
import numpy as np

from .anpr import crop_box, preprocess_plate, recognize_full_crop
from .plate_search import MINIMUM_QUERY_LENGTH, normalize_plate_text

LOGGER = logging.getLogger(__name__)
RUNTIME_OCR_SCHEMA_VERSION = 1


class RuntimeRepository(Protocol):
    """Minimal prediction-only repository interface required by the builder."""

    journeys: list[dict[str, Any]]

    def crop_path(
        self, global_id: str, visit_index: int, sample_index: int
    ) -> Path: ...


@dataclass(frozen=True)
class RuntimeEvidence:
    """One immutable crop-to-journey OCR input."""

    global_id: str
    visit_index: int
    sample_index: int
    tracklet_key: str
    camera: str
    observed_s: float
    crop_sha256: str
    crop_path: Path


def canonical_sha256(value: object) -> str:
    """Hash a JSON value using a stable encoding."""

    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def collect_runtime_evidence(
    repository: RuntimeRepository, *, multi_camera_only: bool = True
) -> list[RuntimeEvidence]:
    """Collect every stored sample in deterministic prediction order."""

    result: list[RuntimeEvidence] = []
    for journey in repository.journeys:
        if multi_camera_only and journey["camera_count"] < 2:
            continue
        for visit_index, visit in enumerate(journey["visits"]):
            for sample_index, sample in enumerate(visit["evidence_samples"]):
                result.append(
                    RuntimeEvidence(
                        global_id=journey["global_id"],
                        visit_index=visit_index,
                        sample_index=sample_index,
                        tracklet_key=visit["tracklet_key"],
                        camera=visit["camera"],
                        observed_s=float(sample["time_s"]),
                        crop_sha256=sample["crop_sha256"],
                        crop_path=repository.crop_path(
                            journey["global_id"], visit_index, sample_index
                        ),
                    )
                )
    return result


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(values, percentile))


def timing_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    """Describe a measured latency sample without implying a benchmark."""

    rows = [float(value) for value in values]
    return {
        "samples": len(rows),
        "mean_ms": float(np.mean(rows)) if rows else None,
        "p50_ms": _percentile(rows, 50),
        "p95_ms": _percentile(rows, 95),
        "max_ms": max(rows) if rows else None,
    }


def _boxes(result: Any) -> list[tuple[list[float], float]]:
    if result.boxes is None:
        return []
    coordinates = result.boxes.xyxy.cpu().numpy().tolist()
    confidences = result.boxes.conf.cpu().numpy().tolist()
    return [
        ([float(value) for value in box], float(confidence))
        for box, confidence in zip(coordinates, confidences, strict=True)
    ]


def select_plate_box(result: Any) -> tuple[list[float], float] | None:
    """Choose one detector box deterministically by score then coordinates."""

    rows = _boxes(result)
    if not rows:
        return None
    rows.sort(key=lambda row: (-row[1], tuple(row[0])))
    return rows[0]


def run_runtime_ocr(
    evidence: list[RuntimeEvidence],
    *,
    detector: Any,
    reader: object,
    image_size: int,
    confidence_threshold: float,
    variant: str,
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Detect and recognize plates without changing vehicle association."""

    started = clock()
    predictions = detector.predict(
        source=[str(row.crop_path) for row in evidence],
        imgsz=image_size,
        conf=confidence_threshold,
        device="cpu",
        stream=True,
        verbose=False,
    )
    entries: list[dict[str, Any]] = []
    exclusions = {
        "no_plate_box": 0,
        "unreadable_crop": 0,
        "invalid_plate_box": 0,
        "empty_or_short_ocr": 0,
    }
    failures: list[dict[str, Any]] = []
    detector_timings: list[float] = []
    ocr_timings: list[float] = []
    combined_timings: list[float] = []
    detector_box_count = 0
    ocr_attempts = 0

    result_count = 0
    for result_count, (target, result) in enumerate(
        zip(evidence, predictions, strict=True), 1
    ):
        detector_ms = float(sum(float(value) for value in result.speed.values()))
        detector_timings.append(detector_ms)
        candidates = _boxes(result)
        detector_box_count += len(candidates)
        selection = select_plate_box(result)
        if selection is None:
            exclusions["no_plate_box"] += 1
            combined_timings.append(detector_ms)
            continue

        image = cv2.imread(str(target.crop_path), cv2.IMREAD_COLOR)
        if image is None:
            exclusions["unreadable_crop"] += 1
            combined_timings.append(detector_ms)
            failures.append(
                {
                    "evidence_key": [
                        target.global_id,
                        target.visit_index,
                        target.sample_index,
                    ],
                    "stage": "read_crop",
                    "error": "unreadable_crop",
                }
            )
            continue
        box, _detector_score = selection
        try:
            plate = crop_box(image, box)
            prepared = preprocess_plate(plate, variant)
        except ValueError:
            exclusions["invalid_plate_box"] += 1
            combined_timings.append(detector_ms)
            failures.append(
                {
                    "evidence_key": [
                        target.global_id,
                        target.visit_index,
                        target.sample_index,
                    ],
                    "stage": "plate_crop",
                    "error": "invalid_plate_box",
                }
            )
            continue

        ocr_attempts += 1
        ocr_started = clock()
        try:
            predicted_text, ocr_score = recognize_full_crop(reader, prepared)
        except (RuntimeError, ValueError) as error:
            ocr_ms = (clock() - ocr_started) * 1000.0
            ocr_timings.append(ocr_ms)
            combined_timings.append(detector_ms + ocr_ms)
            failures.append(
                {
                    "evidence_key": [
                        target.global_id,
                        target.visit_index,
                        target.sample_index,
                    ],
                    "stage": "ocr",
                    "error": type(error).__name__,
                }
            )
            continue
        ocr_ms = (clock() - ocr_started) * 1000.0
        ocr_timings.append(ocr_ms)
        combined_timings.append(detector_ms + ocr_ms)
        normalized_text = normalize_plate_text(predicted_text)
        if len(normalized_text) < MINIMUM_QUERY_LENGTH:
            exclusions["empty_or_short_ocr"] += 1
            continue
        if not math.isfinite(float(ocr_score)) or not 0.0 <= float(ocr_score) <= 1.0:
            failures.append(
                {
                    "evidence_key": [
                        target.global_id,
                        target.visit_index,
                        target.sample_index,
                    ],
                    "stage": "ocr",
                    "error": "invalid_ocr_score",
                }
            )
            continue
        entries.append(
            {
                "global_id": target.global_id,
                "visit_index": target.visit_index,
                "sample_index": target.sample_index,
                "tracklet_key": target.tracklet_key,
                "camera": target.camera,
                "observed_s": target.observed_s,
                "crop_sha256": target.crop_sha256,
                "predicted_plate_text": normalized_text,
                "ocr_score": float(ocr_score),
            }
        )
        if result_count % 25 == 0 or result_count == len(evidence):
            LOGGER.info(
                "runtime_ocr_progress processed=%d total=%d indexed=%d",
                result_count,
                len(evidence),
                len(entries),
            )

    if result_count != len(evidence):
        raise ValueError(
            "Detector returned a different result count than runtime evidence"
        )
    entries.sort(
        key=lambda row: (
            row["global_id"],
            row["visit_index"],
            row["sample_index"],
        )
    )
    report = {
        "counts": {
            "input_evidence": len(evidence),
            "detector_boxes": detector_box_count,
            "ocr_attempts": ocr_attempts,
            "indexed_entries": len(entries),
            "excluded": exclusions,
            "failures": len(failures),
        },
        "timing_ms": {
            "detector_per_evidence": timing_summary(detector_timings),
            "ocr_per_attempt": timing_summary(ocr_timings),
            "combined_per_evidence": timing_summary(combined_timings),
            "batch_wall_ms": (clock() - started) * 1000.0,
        },
        "failures": failures,
    }
    return entries, report


def build_plate_index(
    *,
    scenario: str,
    journeys_sha256: str,
    selection_report_sha256: str,
    sealed_test_report_sha256: str,
    runtime_manifest_sha256: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the strict prediction-linked index consumed by the demo."""

    return {
        "schema_version": RUNTIME_OCR_SCHEMA_VERSION,
        "source": {
            "scenario": scenario,
            "journeys_sha256": journeys_sha256,
        },
        "ocr_provenance": {
            "ocr_selection_report_sha256": selection_report_sha256,
            "sealed_ocr_test_report_sha256": sealed_test_report_sha256,
            "runtime_ocr_manifest_sha256": runtime_manifest_sha256,
        },
        "entries": entries,
    }
