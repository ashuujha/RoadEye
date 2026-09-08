"""Build an ignored, ground-truth-blind queue for sealed ANPR review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from roadeye.plate_review import (  # noqa: E402
    build_test_review_triage,
    public_triage_summary,
    read_json,
    read_jsonl,
    read_review_statuses,
    test_family_records,
    validate_frozen_ocr_selection,
    write_triage_csv,
)
from roadeye.tracklets import sha256, write_json  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "anpr.json"
SELECTION_PATH = ROOT / "reports" / "anpr-ocr-selection.json"
OUTPUT_JSON = ROOT / "artifacts" / "anpr" / "plate-review-triage.json"
OUTPUT_CSV = ROOT / "artifacts" / "anpr" / "plate-review-triage.csv"


def resolve_from_root(value: str | Path) -> Path:
    """Resolve a configured repository-relative path."""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def build(config_path: Path) -> dict:
    """Validate frozen inputs and write the private review queue."""

    config = read_json(config_path)
    selection = validate_frozen_ocr_selection(ROOT, SELECTION_PATH)
    manifest_path = resolve_from_root(config["split_manifest"])
    prediction_path = resolve_from_root(config["test_predictions"])
    transcription_path = resolve_from_root(config["transcriptions"])
    manifest = read_json(manifest_path)
    records = test_family_records(manifest)
    statuses = read_review_statuses(transcription_path, manifest, records)
    report = build_test_review_triage(
        manifest=manifest,
        predictions=read_jsonl(prediction_path),
        statuses=statuses,
        selected_variant=str(selection["selected_variant"]),
    )
    report["provenance"] = {
        "selection": str(SELECTION_PATH.relative_to(ROOT)).replace("\\", "/"),
        "selection_sha256": sha256(SELECTION_PATH),
        "split_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "split_manifest_sha256": sha256(manifest_path),
        "test_predictions": str(prediction_path.relative_to(ROOT)).replace("\\", "/"),
        "test_predictions_sha256": sha256(prediction_path),
        "transcriptions": str(transcription_path.relative_to(ROOT)).replace("\\", "/"),
        "transcriptions_sha256": sha256(transcription_path),
    }
    write_json(OUTPUT_JSON, report)
    write_triage_csv(OUTPUT_CSV, report)

    summary = public_triage_summary(report)
    summary["outputs"] = {
        "json": str(OUTPUT_JSON.relative_to(ROOT)).replace("\\", "/"),
        "json_sha256": sha256(OUTPUT_JSON),
        "csv": str(OUTPUT_CSV.relative_to(ROOT)).replace("\\", "/"),
        "csv_sha256": sha256(OUTPUT_CSV),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config_path = resolve_from_root(args.config)
    print(json.dumps(build(config_path), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
