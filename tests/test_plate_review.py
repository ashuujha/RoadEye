from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from roadeye.plate_review import (
    build_test_review_triage,
    read_review_statuses,
    validate_frozen_ocr_selection,
)
from roadeye.tracklets import text_sha256


def _manifest(count: int = 8) -> dict:
    return {
        "records": [
            {
                "image_id": f"plate-{index}",
                "image_sha256": f"hash-{index}",
                "series": "plate_crop",
                "split": "test",
                "family_representative": True,
            }
            for index in range(count)
        ]
    }


def _predictions(count: int = 8) -> list[dict]:
    return [
        {
            "image_id": f"plate-{index}",
            "split": "test",
            "variant": "color_upscale",
            "text": f"SUGGESTION{index}",
            "score": index / 10,
        }
        for index in range(count)
    ]


def _write_transcriptions(path: Path, plate_texts: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "image_id",
                "image_sha256",
                "split",
                "plate_text",
                "review_status",
            ),
        )
        writer.writeheader()
        for index, plate_text in enumerate(plate_texts):
            writer.writerow(
                {
                    "image_id": f"plate-{index}",
                    "image_sha256": f"hash-{index}",
                    "split": "test",
                    "plate_text": plate_text,
                    "review_status": "",
                }
            )


def test_triage_is_deterministic_and_low_scores_come_first() -> None:
    statuses = {f"plate-{index}": None for index in range(8)}
    report = build_test_review_triage(
        _manifest(), _predictions(), statuses, "color_upscale"
    )

    assert [item["image_id"] for item in report["queue"]] == [
        f"plate-{index}" for index in range(8)
    ]
    assert report["triage_band_counts"] == {
        "invalid_status": 0,
        "manual_attention": 2,
        "standard": 4,
        "quick_check": 2,
    }
    assert report["readiness_status"] == "FAIL"
    assert report["claim_boundaries"]["suggestions_are_ground_truth"] is False


def test_terminal_rows_are_counted_and_excluded_from_queue() -> None:
    statuses = {f"plate-{index}": None for index in range(8)}
    statuses.update(
        {
            "plate-0": "reviewed",
            "plate-1": "corrected",
            "plate-2": "unreadable",
        }
    )
    report = build_test_review_triage(
        _manifest(), _predictions(), statuses, "color_upscale", minimum_readable=2
    )

    assert report["queue_count"] == 5
    assert report["review_status_counts"]["terminal"] == 3
    assert report["review_status_counts"]["readable"] == 2
    assert report["readiness_status"] == "FAIL"


def test_invalid_status_is_triaged_before_pending_rows() -> None:
    statuses = {f"plate-{index}": None for index in range(8)}
    statuses["plate-6"] = "accepted"
    report = build_test_review_triage(
        _manifest(), _predictions(), statuses, "color_upscale"
    )

    assert report["queue"][0]["image_id"] == "plate-6"
    assert report["queue"][0]["triage_band"] == "invalid_status"
    assert report["review_status_counts"]["unrecognized_status"] == 1


def test_status_reader_does_not_depend_on_plate_text(tmp_path: Path) -> None:
    manifest = _manifest(2)
    target_records = {
        record["image_id"]: record for record in manifest["records"]
    }
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_transcriptions(first, ["SECRET-A", "SECRET-B"])
    _write_transcriptions(second, ["DIFFERENT-A", "DIFFERENT-B"])

    assert read_review_statuses(first, manifest, target_records) == (
        read_review_statuses(second, manifest, target_records)
    )


def test_incomplete_prediction_grid_is_rejected() -> None:
    statuses = {f"plate-{index}": None for index in range(8)}
    with pytest.raises(ValueError, match="prediction coverage mismatch"):
        build_test_review_triage(
            _manifest(), _predictions()[:-1], statuses, "color_upscale"
        )


def test_frozen_selection_rejects_changed_source(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "status": "PASS",
                "selected_variant": "color_upscale",
                "frozen_sha256": {"source.py": text_sha256(source)},
            }
        ),
        encoding="utf-8",
    )
    source.write_text("value = 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Frozen OCR input changed"):
        validate_frozen_ocr_selection(tmp_path, selection)
