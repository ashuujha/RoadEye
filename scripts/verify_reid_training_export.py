"""Prove that a RoadEye Re-ID export reloads and infers on CPU exactly."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import torch
import torchvision

from roadeye.phase2 import ROOT
from roadeye.reid_training import export_encoder
from roadeye.tracklets import sha256, write_json
from roadeye.vehicle_encoder import load_roadeye_encoder, load_vehicle_encoder


def verify(initial_weights: Path, output: Path, report_path: Path) -> dict:
    """Round-trip the real architecture and compare deterministic CPU outputs."""
    started = time.perf_counter()
    torch.set_num_threads(1)
    model = load_vehicle_encoder(initial_weights)
    export = export_encoder(
        model,
        output,
        {
            "schema_version": 1,
            "purpose": "cpu_export_import_smoke_only_not_a_trained_result",
            "initial_weights_sha256": sha256(initial_weights),
        },
    )
    loaded = load_roadeye_encoder(output, export["weights_sha256"])
    pixels = torch.linspace(0, 255, 3 * 256 * 256).reshape(1, 3, 256, 256)
    with torch.inference_mode():
        before = model(pixels)
        after = loaded(pixels)
    maximum_absolute_difference = float(torch.max(torch.abs(before - after)))
    report = {
        "status": "PASS" if torch.equal(before, after) else "FAIL",
        "scope": "real_vehicle_encoder_export_exact_reload_and_cpu_inference",
        "not_an_accuracy_result": True,
        "weights_file": output.name,
        "weights_sha256": export["weights_sha256"],
        "embedding_shape": list(after.shape),
        "exact_tensor_equality": bool(torch.equal(before, after)),
        "maximum_absolute_difference": maximum_absolute_difference,
        "all_parameters_frozen_after_load": all(
            not parameter.requires_grad for parameter in loaded.parameters()
        ),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "cuda_available": torch.cuda.is_available(),
        "elapsed_seconds": time.perf_counter() - started,
    }
    write_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--initial-weights",
        type=Path,
        default=ROOT / "artifacts/models/veri_sbs_R50-ibn.pth",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/reid-training/cpu-smoke/roadeye_cityflow_reid.pt",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/reid-training-cpu-smoke.json",
    )
    args = parser.parse_args()
    print(json.dumps(verify(args.initial_weights, args.output, args.report), indent=2))


if __name__ == "__main__":
    main()
