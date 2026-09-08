"""Ground-truth-safe plate-search boundary for frozen demo predictions."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLATE_SEARCH_SCHEMA_VERSION = 1
MINIMUM_QUERY_LENGTH = 3
BLOCKED_AVAILABILITY = "BLOCKED_PENDING_SEALED_OCR"
READY_AVAILABILITY = "READY"
PREDICTION_LABEL = "predicted_plate_text_not_ground_truth"
SCORE_NOTICE = "OCR scores are uncalibrated model values, not probabilities."
CLAIM_NOTICE = (
    "Plate matches will be runtime OCR predictions linked to frozen journey evidence; "
    "they are not ownership records or benchmark ground truth."
)
DEFAULT_BLOCKED_REASON = (
    "Plate search is awaiting the sealed OCR evaluation and a hash-bound runtime "
    "prediction index. No plate matches are available yet."
)

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_INDEX_KEYS = {"schema_version", "source", "ocr_provenance", "entries"}
_SOURCE_KEYS = {"scenario", "journeys_sha256"}
_PROVENANCE_KEYS = {
    "ocr_selection_report_sha256",
    "sealed_ocr_test_report_sha256",
    "runtime_ocr_manifest_sha256",
}
_ENTRY_KEYS = {
    "global_id",
    "visit_index",
    "sample_index",
    "tracklet_key",
    "camera",
    "observed_s",
    "crop_sha256",
    "predicted_plate_text",
    "ocr_score",
}


def normalize_plate_text(value: str) -> str:
    """Return an uppercase alphanumeric plate-search representation."""

    return "".join(
        character
        for character in value.upper()
        if character.isascii() and character.isalnum()
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_exact_keys(value: Any, expected: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} must contain exactly {sorted(expected)}")
    return value


def _require_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_index(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class _PlateEntry:
    global_id: str
    visit_index: int
    sample_index: int
    tracklet_key: str
    camera: str
    observed_s: float
    crop_sha256: str
    predicted_plate_text: str
    normalized_plate_text: str
    ocr_score: float

    def public_result(self, *, match_kind: str) -> dict[str, Any]:
        return {
            "global_id": self.global_id,
            "journey_url": f"/api/vehicles/{self.global_id}",
            "visit_index": self.visit_index,
            "sample_index": self.sample_index,
            "tracklet_key": self.tracklet_key,
            "camera": self.camera,
            "observed_s": self.observed_s,
            "crop_sha256": self.crop_sha256,
            "crop_url": (
                f"/api/vehicles/{self.global_id}/visits/{self.visit_index}/samples/"
                f"{self.sample_index}/crop"
            ),
            "predicted_plate_text": self.predicted_plate_text,
            "normalized_plate_text": self.normalized_plate_text,
            "match_kind": match_kind,
            "ocr_score": self.ocr_score,
            "score_kind": "uncalibrated_ocr_model_score_not_probability",
            "is_probability": False,
            "prediction_status": PREDICTION_LABEL,
        }


class PlateSearchIndex:
    """Validated optional index over OCR predictions attached to runtime evidence."""

    def __init__(
        self,
        *,
        availability: str,
        reason: str,
        entries: tuple[_PlateEntry, ...] = (),
        source_prediction_sha256: str | None = None,
        provenance: dict[str, str] | None = None,
    ) -> None:
        self.availability = availability
        self.reason = reason
        self.entries = entries
        self.source_prediction_sha256 = source_prediction_sha256
        self.provenance = provenance

    @classmethod
    def from_config(
        cls,
        settings: Any,
        *,
        artifact_root: Path,
        journeys: list[dict[str, Any]],
        scenario: str,
        source_prediction_sha256: str,
    ) -> PlateSearchIndex:
        if settings is None:
            return cls(availability=BLOCKED_AVAILABILITY, reason=DEFAULT_BLOCKED_REASON)
        if not isinstance(settings, dict):
            raise ValueError("plate_search configuration must be an object")
        enabled = settings.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("plate_search.enabled must be a boolean")
        if not enabled:
            allowed = {"enabled", "availability", "reason"}
            if set(settings) != allowed:
                raise ValueError(
                    "disabled plate_search configuration must contain exactly "
                    f"{sorted(allowed)}"
                )
            if settings["availability"] != BLOCKED_AVAILABILITY:
                raise ValueError("disabled plate search must declare its blocked state")
            reason = settings["reason"]
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("disabled plate search requires a reason")
            return cls(availability=BLOCKED_AVAILABILITY, reason=reason.strip())

        allowed = {"enabled", "availability", "index", "index_sha256"}
        if set(settings) != allowed:
            raise ValueError(
                "enabled plate_search configuration must contain exactly "
                f"{sorted(allowed)}"
            )
        if settings["availability"] != READY_AVAILABILITY:
            raise ValueError("enabled plate search must declare READY availability")
        relative_path = settings["index"]
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError("enabled plate search requires an index path")
        index_path = (artifact_root / relative_path).resolve()
        if not index_path.is_relative_to(artifact_root.resolve()):
            raise ValueError("plate search index path escapes runtime artifacts")
        if not index_path.is_file():
            raise ValueError("plate search index is missing")
        expected_hash = _require_sha256(
            settings["index_sha256"], label="plate search index hash"
        )
        if _sha256(index_path) != expected_hash:
            raise ValueError("plate search index hash mismatch")
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        return cls._from_payload(
            payload,
            journeys=journeys,
            scenario=scenario,
            source_prediction_sha256=source_prediction_sha256,
        )

    @classmethod
    def _from_payload(
        cls,
        payload: Any,
        *,
        journeys: list[dict[str, Any]],
        scenario: str,
        source_prediction_sha256: str,
    ) -> PlateSearchIndex:
        index = _require_exact_keys(payload, _INDEX_KEYS, label="plate search index")
        if index["schema_version"] != PLATE_SEARCH_SCHEMA_VERSION:
            raise ValueError("unsupported plate search index schema")
        source = _require_exact_keys(
            index["source"], _SOURCE_KEYS, label="plate search source"
        )
        if source["scenario"] != scenario:
            raise ValueError("plate search scenario does not match demo runtime")
        if source["journeys_sha256"] != source_prediction_sha256:
            raise ValueError("plate search journey hash does not match demo runtime")
        _require_sha256(source["journeys_sha256"], label="source journey hash")

        raw_provenance = _require_exact_keys(
            index["ocr_provenance"],
            _PROVENANCE_KEYS,
            label="plate search OCR provenance",
        )
        provenance = {
            key: _require_sha256(value, label=key)
            for key, value in raw_provenance.items()
        }
        raw_entries = index["entries"]
        if not isinstance(raw_entries, list):
            raise ValueError("plate search entries must be a list")

        journeys_by_id = {journey["global_id"]: journey for journey in journeys}
        entries = tuple(
            cls._validate_entry(raw, journeys_by_id=journeys_by_id, row_index=row_index)
            for row_index, raw in enumerate(raw_entries)
        )
        evidence_keys = {
            (entry.global_id, entry.visit_index, entry.sample_index) for entry in entries
        }
        if len(evidence_keys) != len(entries):
            raise ValueError("plate search index contains duplicate evidence entries")
        return cls(
            availability=READY_AVAILABILITY,
            reason="",
            entries=entries,
            source_prediction_sha256=source_prediction_sha256,
            provenance=provenance,
        )

    @staticmethod
    def _validate_entry(
        raw: Any,
        *,
        journeys_by_id: dict[str, dict[str, Any]],
        row_index: int,
    ) -> _PlateEntry:
        entry = _require_exact_keys(
            raw, _ENTRY_KEYS, label=f"plate search entry {row_index}"
        )
        global_id = entry["global_id"]
        if not isinstance(global_id, str) or global_id not in journeys_by_id:
            raise ValueError(f"plate search entry {row_index} has unknown global_id")
        visit_index = _require_index(
            entry["visit_index"], label=f"entry {row_index} visit_index"
        )
        sample_index = _require_index(
            entry["sample_index"], label=f"entry {row_index} sample_index"
        )
        try:
            visit = journeys_by_id[global_id]["visits"][visit_index]
            sample = visit["evidence_samples"][sample_index]
        except IndexError as error:
            raise ValueError(
                f"plate search entry {row_index} references unknown evidence"
            ) from error
        if entry["tracklet_key"] != visit["tracklet_key"]:
            raise ValueError(f"plate search entry {row_index} tracklet mismatch")
        if entry["camera"] != visit["camera"]:
            raise ValueError(f"plate search entry {row_index} camera mismatch")
        observed_s = entry["observed_s"]
        if isinstance(observed_s, bool) or not isinstance(observed_s, (int, float)):
            raise ValueError(f"plate search entry {row_index} observed_s must be numeric")
        if not math.isfinite(float(observed_s)) or not math.isclose(
            float(observed_s), float(sample["time_s"]), rel_tol=0.0, abs_tol=1e-9
        ):
            raise ValueError(f"plate search entry {row_index} timestamp mismatch")
        crop_sha256 = _require_sha256(
            entry["crop_sha256"], label=f"entry {row_index} crop hash"
        )
        if crop_sha256 != sample["crop_sha256"]:
            raise ValueError(f"plate search entry {row_index} crop hash mismatch")
        predicted_text = entry["predicted_plate_text"]
        if not isinstance(predicted_text, str):
            raise ValueError(f"plate search entry {row_index} plate text must be a string")
        normalized_text = normalize_plate_text(predicted_text)
        if len(normalized_text) < MINIMUM_QUERY_LENGTH:
            raise ValueError(f"plate search entry {row_index} has unusable plate text")
        ocr_score = entry["ocr_score"]
        if (
            isinstance(ocr_score, bool)
            or not isinstance(ocr_score, (int, float))
            or not math.isfinite(float(ocr_score))
            or not 0.0 <= float(ocr_score) <= 1.0
        ):
            raise ValueError(f"plate search entry {row_index} OCR score is invalid")
        return _PlateEntry(
            global_id=global_id,
            visit_index=visit_index,
            sample_index=sample_index,
            tracklet_key=entry["tracklet_key"],
            camera=entry["camera"],
            observed_s=float(observed_s),
            crop_sha256=crop_sha256,
            predicted_plate_text=predicted_text,
            normalized_plate_text=normalized_text,
            ocr_score=float(ocr_score),
        )

    def status(self) -> dict[str, Any]:
        return {
            "status": "UNVERIFIED",
            "availability": self.availability,
            "enabled": self.availability == READY_AVAILABILITY,
            "reason": self.reason or None,
            "index_entry_count": len(self.entries),
            "minimum_query_length": MINIMUM_QUERY_LENGTH,
            "prediction_label": PREDICTION_LABEL,
            "score_notice": SCORE_NOTICE,
            "claim_notice": CLAIM_NOTICE,
            "source_prediction_sha256": self.source_prediction_sha256,
            "ocr_provenance": self.provenance,
        }

    def search(self, query: str, *, limit: int = 25) -> dict[str, Any]:
        query_text = query.strip()
        normalized_query = normalize_plate_text(query_text)
        response = {
            **self.status(),
            "query": query_text,
            "normalized_query": normalized_query,
            "result_count": 0,
            "results": [],
        }
        if self.availability != READY_AVAILABILITY:
            return response
        if len(normalized_query) < MINIMUM_QUERY_LENGTH:
            raise ValueError(
                f"Plate query must contain at least {MINIMUM_QUERY_LENGTH} "
                "alphanumeric characters"
            )
        ranked: list[tuple[int, float, str, int, int, _PlateEntry, str]] = []
        for entry in self.entries:
            if entry.normalized_plate_text == normalized_query:
                match_kind = "exact"
                rank = 0
            elif entry.normalized_plate_text.startswith(normalized_query):
                match_kind = "prefix"
                rank = 1
            elif normalized_query in entry.normalized_plate_text:
                match_kind = "contains"
                rank = 2
            else:
                continue
            ranked.append(
                (
                    rank,
                    -entry.ocr_score,
                    entry.global_id,
                    entry.visit_index,
                    entry.sample_index,
                    entry,
                    match_kind,
                )
            )
        ranked.sort(key=lambda row: row[:5])
        results = [
            entry.public_result(match_kind=match_kind)
            for *_, entry, match_kind in ranked[:limit]
        ]
        response["result_count"] = len(results)
        response["results"] = results
        return response
