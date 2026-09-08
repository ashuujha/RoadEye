"""Tests for the prediction-linked plate-search artifact boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from roadeye.plate_search import (
    BLOCKED_AVAILABILITY,
    PREDICTION_LABEL,
    READY_AVAILABILITY,
    PlateSearchIndex,
    normalize_plate_text,
)


SOURCE_HASH = "f" * 64


def journeys() -> list[dict[str, Any]]:
    rows = []
    for index, camera in enumerate(("c1", "c2", "c3")):
        key = f"validation/S02/{camera}/{index + 1}"
        rows.append(
            {
                "global_id": f"roadeye_{index}",
                "visits": [
                    {
                        "tracklet_key": key,
                        "camera": camera,
                        "evidence_samples": [
                            {
                                "time_s": float(index),
                                "crop_sha256": str(index + 1) * 64,
                            }
                        ],
                    }
                ],
            }
        )
    return rows


def entry(index: int, plate_text: str, score: float) -> dict[str, Any]:
    camera = f"c{index + 1}"
    return {
        "global_id": f"roadeye_{index}",
        "visit_index": 0,
        "sample_index": 0,
        "tracklet_key": f"validation/S02/{camera}/{index + 1}",
        "camera": camera,
        "observed_s": float(index),
        "crop_sha256": str(index + 1) * 64,
        "predicted_plate_text": plate_text,
        "ocr_score": score,
    }


def payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": {
            "scenario": "S02_fixture",
            "journeys_sha256": SOURCE_HASH,
        },
        "ocr_provenance": {
            "ocr_selection_report_sha256": "a" * 64,
            "sealed_ocr_test_report_sha256": "b" * 64,
            "runtime_ocr_manifest_sha256": "c" * 64,
        },
        "entries": [
            entry(0, "KA-01-AB-1234", 0.72),
            entry(1, "KA01-CD-5678", 0.91),
            entry(2, "XX-KA01-ZZ", 0.99),
        ],
    }


def load_index(tmp_path: Path, value: dict[str, Any]) -> PlateSearchIndex:
    path = tmp_path / "plate-index.json"
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    settings = {
        "enabled": True,
        "availability": READY_AVAILABILITY,
        "index": "plate-index.json",
        "index_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    return PlateSearchIndex.from_config(
        settings,
        artifact_root=tmp_path,
        journeys=journeys(),
        scenario="S02_fixture",
        source_prediction_sha256=SOURCE_HASH,
    )


def test_disabled_plate_search_returns_no_synthetic_results(tmp_path):
    index = PlateSearchIndex.from_config(
        {
            "enabled": False,
            "availability": BLOCKED_AVAILABILITY,
            "reason": "Awaiting sealed OCR.",
        },
        artifact_root=tmp_path,
        journeys=journeys(),
        scenario="S02_fixture",
        source_prediction_sha256=SOURCE_HASH,
    )
    assert index.status()["status"] == "UNVERIFIED"
    assert index.status()["availability"] == BLOCKED_AVAILABILITY
    assert index.search("KA01")["results"] == []
    assert index.search("KA01")["result_count"] == 0


def test_ready_index_normalizes_ranks_and_labels_prediction_matches(tmp_path):
    index = load_index(tmp_path, payload())
    assert normalize_plate_text("ka-01 ab.1234") == "KA01AB1234"
    assert normalize_plate_text("KA01" + chr(1072) + "B1234") == "KA01B1234"
    exact = index.search("ka 01-ab 1234")
    assert exact["results"][0]["match_kind"] == "exact"
    assert exact["results"][0]["prediction_status"] == PREDICTION_LABEL
    assert exact["results"][0]["is_probability"] is False

    partial = index.search("KA01")
    assert [row["match_kind"] for row in partial["results"]] == [
        "prefix",
        "prefix",
        "contains",
    ]
    assert [row["global_id"] for row in partial["results"]] == [
        "roadeye_1",
        "roadeye_0",
        "roadeye_2",
    ]
    assert index.status()["source_prediction_sha256"] == SOURCE_HASH


def test_ready_index_rejects_short_queries(tmp_path):
    index = load_index(tmp_path, payload())
    with pytest.raises(ValueError, match="at least 3"):
        index.search("K-1")


def test_index_hash_is_checked_before_loading(tmp_path):
    path = tmp_path / "plate-index.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="index hash mismatch"):
        PlateSearchIndex.from_config(
            {
                "enabled": True,
                "availability": READY_AVAILABILITY,
                "index": "plate-index.json",
                "index_sha256": digest,
            },
            artifact_root=tmp_path,
            journeys=journeys(),
            scenario="S02_fixture",
            source_prediction_sha256=SOURCE_HASH,
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value["source"].update(journeys_sha256="0" * 64), "journey hash"),
        (lambda value: value["entries"][0].update(global_id="unknown"), "unknown global_id"),
        (lambda value: value["entries"][0].update(crop_sha256="0" * 64), "crop hash"),
        (lambda value: value["entries"][0].update(owner_name="forbidden"), "exactly"),
    ],
)
def test_index_rejects_unbound_or_extra_data(tmp_path, change, message):
    value = payload()
    change(value)
    with pytest.raises(ValueError, match=message):
        load_index(tmp_path, value)
