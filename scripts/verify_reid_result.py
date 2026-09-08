"""Validate a returned private Re-ID result before runtime or evaluation use."""

from __future__ import annotations

import argparse
import json
import math
import platform
import shutil
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

import torch

from roadeye.phase2 import ROOT
from roadeye.tracklets import sha256, write_json
from roadeye.vehicle_encoder import load_roadeye_encoder

EXPECTED_MEMBERS = {
    "history.json",
    "roadeye_cityflow_reid.json",
    "roadeye_cityflow_reid.pt",
}


def _safe_members(names: list[str]) -> bool:
    return all(
        not PurePosixPath(name).is_absolute()
        and ".." not in PurePosixPath(name).parts
        and "\\" not in name
        for name in names
    )


def verify(
    result_zip: Path,
    output: Path,
    config_path: Path,
    bundle_report_path: Path,
    report_path: Path,
) -> dict:
    """Validate hashes, selection history, isolation declarations, and CPU load."""
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite returned artifact: {output}")
    config_hash = sha256(config_path)
    bundle_report = json.loads(bundle_report_path.read_text(encoding="utf-8"))
    archive_hash = sha256(result_zip)
    with zipfile.ZipFile(result_zip) as archive:
        names = archive.namelist()
        if set(names) != EXPECTED_MEMBERS or not _safe_members(names):
            raise ValueError("Unexpected or unsafe returned archive members")
        if archive.testzip() is not None:
            raise ValueError("Returned archive CRC check failed")
        manifest = json.loads(archive.read("roadeye_cityflow_reid.json"))
        history = json.loads(archive.read("history.json"))
        output.mkdir(parents=True)
        for name in sorted(EXPECTED_MEMBERS):
            with archive.open(name) as source, (output / name).open("wb") as target:
                shutil.copyfileobj(source, target)

    if manifest["training_scenarios"] != ["S01", "S03"]:
        raise ValueError("Unexpected training scenarios")
    if manifest["evaluation_scenarios_used"]:
        raise ValueError("Evaluation labels were declared during training")
    if manifest["split_unit"] != "scoped_identity":
        raise ValueError("Training split is not identity-disjoint")
    if manifest["training_config_sha256"] != config_hash:
        raise ValueError("Returned training config hash mismatch")
    if manifest["bundle_manifest_sha256"] != bundle_report["bundle_manifest_sha256"]:
        raise ValueError("Returned training bundle hash mismatch")
    weights = output / manifest["weights_file"]
    if sha256(weights) != manifest["weights_sha256"]:
        raise ValueError("Returned weights hash mismatch")
    if [row["epoch"] for row in history] != list(range(16)):
        raise ValueError("Expected epoch zero and 15 completed epochs")
    if not all(
        math.isfinite(float(value))
        for row in history[1:]
        for value in (
            row["loss"],
            row["cross_entropy"],
            row["triplet"],
            row["development"]["rank1"],
            row["development"]["map"],
        )
    ):
        raise ValueError("Non-finite training history")
    best = max(
        history,
        key=lambda row: (
            row["development"]["map"] or -1,
            row["development"]["rank1"] or -1,
            -row["epoch"],
        ),
    )
    if (
        best["epoch"] != manifest["best_epoch"]
        or best["development"] != manifest["development_metrics"]
        or history[0]["development"] != manifest["baseline_development_metrics"]
    ):
        raise ValueError("Returned best-epoch selection is inconsistent")

    started = time.perf_counter()
    torch.set_num_threads(1)
    model = load_roadeye_encoder(weights, manifest["weights_sha256"])
    pixels = torch.linspace(0, 255, 3 * 256 * 256).reshape(1, 3, 256, 256)
    with torch.inference_mode():
        embedding = model(pixels)
    baseline = manifest["baseline_development_metrics"]
    selected = manifest["development_metrics"]
    report = {
        "status": "PASS",
        "scope": "returned_reid_artifact_integrity_selection_and_cpu_acceptance",
        "result_zip": {
            "filename": result_zip.name,
            "bytes": result_zip.stat().st_size,
            "sha256": archive_hash,
            "members": sorted(EXPECTED_MEMBERS),
            "zip_test": "PASS",
        },
        "manifest_sha256": sha256(output / "roadeye_cityflow_reid.json"),
        "history_sha256": sha256(output / "history.json"),
        "weights_sha256": manifest["weights_sha256"],
        "training_scenarios": manifest["training_scenarios"],
        "evaluation_scenarios_used": manifest["evaluation_scenarios_used"],
        "split_unit": manifest["split_unit"],
        "epochs_completed": manifest["epochs_completed"],
        "best_epoch": manifest["best_epoch"],
        "development": {
            "queries": selected["queries"],
            "baseline_rank1": baseline["rank1"],
            "selected_rank1": selected["rank1"],
            "rank1_absolute_change": selected["rank1"] - baseline["rank1"],
            "baseline_map": baseline["map"],
            "selected_map": selected["map"],
            "map_absolute_change": selected["map"] - baseline["map"],
            "scope": selected["scope"],
        },
        "training_environment": {
            key: manifest[key]
            for key in ("python", "platform", "torch", "torchvision", "cuda_device")
        },
        "training_python_3_11_status": "PASS"
        if manifest["python"].startswith("3.11.")
        else "FAIL",
        "training_code_archive_linkage_status": "PASS"
        if "training_code_sha256" in manifest
        else "UNVERIFIED",
        "cpu_acceptance": {
            "status": "PASS",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": torch.__version__,
            "embedding_shape": list(embedding.shape),
            "finite": bool(torch.isfinite(embedding).all()),
            "all_parameters_frozen": all(
                not parameter.requires_grad for parameter in model.parameters()
            ),
            "elapsed_seconds": time.perf_counter() - started,
        },
        "accuracy_claim": "development identity-camera pooled retrieval only",
        "fresh_evaluation_scenario": "S02",
    }
    if not report["cpu_acceptance"]["finite"]:
        raise ValueError("Returned encoder produced non-finite CPU output")
    write_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result-zip",
        type=Path,
        default=ROOT / "artifacts/reid-training/returned/roadeye-reid-result.zip",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/reid-training.json",
    )
    parser.add_argument(
        "--bundle-report",
        type=Path,
        default=ROOT / "reports/reid-training-bundle.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/reid-trained-model.json",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            verify(
                args.result_zip,
                args.output,
                args.config,
                args.bundle_report,
                args.report,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
