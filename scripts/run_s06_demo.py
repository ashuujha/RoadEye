"""Run frozen RoadEye inference on S06 without ground truth or scoring."""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from roadeye.phase2 import ROOT, run
from roadeye.s06_demo import S06_DISCLOSURE, build_s06_report, markdown_report
from roadeye.tracklets import sha256, text_sha256, write_json

CONFIG = ROOT / "configs/s06-demo.json"
WINDOW = ROOT / "configs/s06-demo-window.json"
SELECTION = ROOT / "reports/reid-six-camera-repair-selection.json"
OUTPUT = ROOT / "artifacts/s06-demo-unverified-runtime"
REPORT_JSON = ROOT / "reports/s06-demo-prediction.json"
REPORT_MD = ROOT / "reports/s06-demo-prediction.md"


@contextmanager
def reject_ground_truth_and_evaluation_outputs():
    """Fail closed if runtime tries to open a GT file or evaluation directory."""
    original = Path.open

    def guarded_open(path: Path, *args, **kwargs):
        parts = {part.casefold() for part in path.parts}
        if path.name.casefold() == "gt.txt" or "evaluation" in parts:
            raise RuntimeError(f"S06 prediction attempted prohibited access: {path}")
        return original(path, *args, **kwargs)

    with patch.object(Path, "open", guarded_open):
        yield


def load_and_validate_frozen_inputs() -> tuple[dict, dict, dict]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    window = json.loads(WINDOW.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    if config.get("disclosure") != S06_DISCLOSURE:
        raise ValueError("S06 configuration is missing the mandatory disclosure")
    if window.get("disclosure") != S06_DISCLOSURE:
        raise ValueError("S06 window is missing the mandatory disclosure")
    if config["association"] != selection["selected_policy"]:
        raise ValueError("S06 association policy differs from frozen S01/S03 selection")
    if selection.get("selected_hsv_weight") != 0.0:
        raise ValueError("S06 runner supports the selected pure-ReID descriptor only")
    for relative, digest in selection["tracked_text_sha256"].items():
        source = ROOT / relative
        if text_sha256(source) != digest:
            raise ValueError(f"Frozen selection dependency changed: {relative}")
    weights = ROOT / config["embedding"]["weights"]
    expected_model = selection["binary_sha256"]["model"]
    if sha256(weights) != expected_model:
        raise ValueError("S06 model differs from frozen S01/S03 selection")
    if config["embedding"]["weights_sha256"] != expected_model:
        raise ValueError("S06 config model hash differs from frozen selection")
    expected_cameras = {f"c0{number}" for number in range(41, 47)}
    if {row["camera_id"] for row in window["cameras"]} != expected_cameras:
        raise ValueError("S06 window must include c041 through c046")
    if window["start_s"] != 0.0 or window["end_s"] != 199.9:
        raise ValueError("S06 window is not the complete declared interval")
    return config, window, selection


def write_disclosure_sidecar() -> None:
    write_json(
        OUTPUT / "S06_UNVERIFIED_DISCLOSURE.json",
        {
            "status": "UNVERIFIED",
            "disclosure": S06_DISCLOSURE,
            "scope": "Every file in this directory is an internal prediction cache for the disclosed S06 run.",
            "ground_truth_used": False,
            "accuracy_metrics_allowed": False,
        },
    )


def predict() -> dict:
    _, window, selection = load_and_validate_frozen_inputs()
    with reject_ground_truth_and_evaluation_outputs():
        run(CONFIG, OUTPUT)
    write_disclosure_sidecar()
    journeys = json.loads((OUTPUT / "journeys.json").read_text(encoding="utf-8"))
    links = json.loads((OUTPUT / "links.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((OUTPUT / "run.json").read_text(encoding="utf-8"))
    prepared = json.loads((OUTPUT / "prepared.json").read_text(encoding="utf-8"))
    report = build_s06_report(
        journeys=journeys,
        links=links,
        run=run_manifest,
        prepared=prepared,
        window=window,
        selection=selection,
        selection_sha256=sha256(SELECTION),
    )
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(markdown_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "disclosure": report["disclosure"],
                "maximum_predicted_camera_span": report["prediction_summary"][
                    "maximum_predicted_camera_span"
                ],
                "identities_at_maximum_span": report["prediction_summary"][
                    "identities_at_maximum_span"
                ],
                "report": REPORT_JSON.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return report


def verify() -> None:
    load_and_validate_frozen_inputs()
    report_before = sha256(REPORT_JSON)
    with reject_ground_truth_and_evaluation_outputs():
        run(CONFIG, OUTPUT, verify_only=True)
    if sha256(REPORT_JSON) != report_before:
        raise ValueError("Verification changed the S06 public report")
    if not (OUTPUT / "S06_UNVERIFIED_DISCLOSURE.json").is_file():
        raise ValueError("S06 runtime disclosure sidecar is missing")
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    if report.get("disclosure") != S06_DISCLOSURE:
        raise ValueError("S06 public report disclosure is missing")
    print("PASS: deterministic S06 predictions reproduced without GT or scoring")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("predict", "verify"))
    args = parser.parse_args()
    if args.action == "predict":
        predict()
    else:
        verify()


if __name__ == "__main__":
    main()
