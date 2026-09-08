"""Ground-truth-blind triage helpers for the sealed ANPR review queue."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Mapping

from .anpr import GROUND_TRUTH_STATUSES, READABLE_GROUND_TRUTH_STATUSES
from .anpr import validate_ocr_prediction_grid
from .tracklets import sha256, text_sha256

TRIAGE_BANDS = ("manual_attention", "standard", "quick_check")


def read_json(path: Path) -> dict:
    """Read one JSON object from disk."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict]:
    """Read JSON objects from a non-empty JSONL artifact."""

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Expected JSON objects in prediction artifact: {path}")
    return rows


def validate_frozen_ocr_selection(root: Path, selection_path: Path) -> dict:
    """Verify every source frozen before sealed test prediction/review."""

    selection = read_json(selection_path)
    if selection.get("status") != "PASS":
        raise ValueError("OCR selection report is not a passing freeze")
    if not selection.get("selected_variant"):
        raise ValueError("OCR selection report has no selected variant")
    frozen = selection.get("frozen_sha256")
    if not isinstance(frozen, dict) or not frozen:
        raise ValueError("OCR selection report has no frozen source hashes")
    for relative, expected in frozen.items():
        source = root / relative
        actual = (
            text_sha256(source)
            if source.suffix.lower() in {".json", ".py"}
            else sha256(source)
        )
        if actual != expected:
            raise ValueError(f"Frozen OCR input changed: {relative}")
    return selection


def test_family_records(manifest: dict) -> dict[str, dict]:
    """Return the frozen representative test crop records keyed by image ID."""

    records = {
        record["image_id"]: record
        for record in manifest["records"]
        if record["series"] == "plate_crop"
        and record["split"] == "test"
        and record["family_representative"]
    }
    if not records:
        raise ValueError("No frozen representative test plate families found")
    return records


def read_review_statuses(
    path: Path,
    manifest: dict,
    target_records: Mapping[str, dict],
) -> dict[str, str | None]:
    """Read only status/provenance fields; plate text never enters triage."""

    expected_ids = {record["image_id"] for record in manifest["records"]}
    required_columns = {"image_id", "image_sha256", "split", "review_status"}
    statuses: dict[str, str | None] = {}
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required_columns <= set(reader.fieldnames):
            raise ValueError("Transcription CSV is missing required review columns")
        for row in reader:
            image_id = row.get("image_id", "")
            if image_id in seen or image_id not in expected_ids:
                raise ValueError(f"Unknown or duplicate transcription row: {image_id}")
            seen.add(image_id)
            if image_id not in target_records:
                continue
            record = target_records[image_id]
            if row.get("image_sha256") != record["image_sha256"]:
                raise ValueError(f"Transcription image hash mismatch: {image_id}")
            if row.get("split") != "test" or record["split"] != "test":
                raise ValueError(f"Transcription split mismatch: {image_id}")
            statuses[image_id] = row.get("review_status", "")
    for image_id in target_records:
        statuses.setdefault(image_id, None)
    return statuses


def _score(value: object, image_id: str) -> float:
    score = float(value)
    if not math.isfinite(score):
        raise ValueError(f"Non-finite OCR score: {image_id}")
    return score


def _relative_band(position: int, count: int) -> str:
    quartile = math.ceil(count / 4)
    if position < quartile:
        return "manual_attention"
    if position >= count - quartile:
        return "quick_check"
    return "standard"


def build_test_review_triage(
    manifest: dict,
    predictions: list[dict],
    statuses: Mapping[str, str | None],
    selected_variant: str,
    minimum_readable: int = 150,
) -> dict:
    """Build a deterministic queue without reading or inferring plate truth."""

    records = test_family_records(manifest)
    expected_ids = set(records)
    prediction_counts = validate_ocr_prediction_grid(
        predictions,
        expected_ids,
        {selected_variant},
        "test",
    )
    by_id = {row["image_id"]: row for row in predictions}
    review_counts = Counter({status: 0 for status in GROUND_TRUTH_STATUSES})
    missing_status = 0
    unrecognized_status = 0
    invalid_items = []
    pending_items = []
    for image_id in sorted(expected_ids):
        status = statuses.get(image_id)
        if status in GROUND_TRUTH_STATUSES:
            review_counts[str(status)] += 1
            continue
        prediction = by_id[image_id]
        item = {
            "image_id": image_id,
            "image_sha256": records[image_id]["image_sha256"],
            "split": "test",
            "selected_variant": selected_variant,
            "suggested_text": str(prediction.get("text", "")),
            "uncalibrated_ocr_score": _score(prediction.get("score"), image_id),
            "current_review_status": "" if status is None else str(status),
        }
        if status is None or not str(status).strip():
            missing_status += 1
            pending_items.append(item)
        else:
            unrecognized_status += 1
            item["triage_band"] = "invalid_status"
            item["triage_reason"] = "unrecognized_review_status"
            invalid_items.append(item)

    pending_items.sort(key=lambda row: (row["uncalibrated_ocr_score"], row["image_id"]))
    for position, item in enumerate(pending_items):
        band = _relative_band(position, len(pending_items))
        item["triage_band"] = band
        item["triage_reason"] = {
            "manual_attention": "lowest_relative_score_quartile",
            "standard": "middle_relative_score_half",
            "quick_check": "highest_relative_score_quartile",
        }[band]
    invalid_items.sort(key=lambda row: row["image_id"])
    queue = invalid_items + pending_items
    for rank, item in enumerate(queue, 1):
        item["rank"] = rank

    readable = sum(review_counts[status] for status in READABLE_GROUND_TRUTH_STATUSES)
    terminal = sum(review_counts.values())
    band_counts = Counter(item["triage_band"] for item in queue)
    pending_scores = [item["uncalibrated_ocr_score"] for item in pending_items]
    readiness = (
        missing_status == 0
        and unrecognized_status == 0
        and readable >= minimum_readable
    )
    return {
        "schema_version": 1,
        "status": "PASS",
        "scope": "ground_truth_blind_sealed_test_human_review_triage",
        "selected_variant": selected_variant,
        "expected_test_families": len(expected_ids),
        "prediction_counts": prediction_counts,
        "review_status_counts": {
            "reviewed": review_counts["reviewed"],
            "corrected": review_counts["corrected"],
            "unreadable": review_counts["unreadable"],
            "terminal": terminal,
            "missing_status": missing_status,
            "unrecognized_status": unrecognized_status,
            "readable": readable,
            "minimum_readable": minimum_readable,
        },
        "readiness_status": "PASS" if readiness else "FAIL",
        "queue_count": len(queue),
        "triage_band_counts": {
            band: band_counts[band]
            for band in ("invalid_status", *TRIAGE_BANDS)
        },
        "pending_score_summary": {
            "minimum": min(pending_scores) if pending_scores else None,
            "median": statistics.median(pending_scores) if pending_scores else None,
            "maximum": max(pending_scores) if pending_scores else None,
        },
        "ranking": {
            "order": "invalid status first, then ascending uncalibrated OCR score",
            "manual_attention": "lowest relative score quartile",
            "standard": "middle relative score half",
            "quick_check": "highest relative score quartile",
        },
        "claim_boundaries": {
            "suggestions_are_ground_truth": False,
            "score_is_probability": False,
            "ground_truth_fields_used_for_ranking": [],
            "all_test_rows_require_terminal_human_review": True,
            "triage_order_changes_scoring_denominator": False,
        },
        "queue": queue,
    }


def write_triage_csv(path: Path, report: dict) -> None:
    """Write the detailed ignored queue for local human review."""

    columns = (
        "rank",
        "triage_band",
        "triage_reason",
        "image_id",
        "image_sha256",
        "split",
        "selected_variant",
        "suggested_text",
        "uncalibrated_ocr_score",
        "current_review_status",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {column: item[column] for column in columns}
            for item in report["queue"]
        )


def public_triage_summary(report: dict) -> dict:
    """Return counts safe for logs and tracked audit documents."""

    return {
        key: report[key]
        for key in (
            "schema_version",
            "status",
            "scope",
            "selected_variant",
            "expected_test_families",
            "prediction_counts",
            "review_status_counts",
            "readiness_status",
            "queue_count",
            "triage_band_counts",
            "pending_score_summary",
            "ranking",
            "claim_boundaries",
        )
    }
