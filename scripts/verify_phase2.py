"""Verify cached inference without GT/network access and check real-data causality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from roadeye.association import associate
from roadeye.phase2 import ROOT, run
from roadeye.tracklets import Observation, checked_path, sha256, write_json


def guard(event: str, args: tuple) -> None:
    if event == "open" and args and isinstance(args[0], (str, Path)):
        if "gt" in str(args[0]).replace("\\", "/").lower().split("/"):
            raise AssertionError("Inference attempted to access ground truth")
    if event == "socket.connect":
        raise AssertionError("Cached inference attempted network access")
    if event == "import" and args[0] == "roadeye.evaluation":
        raise AssertionError("Inference imported evaluator")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/phase2-repaired"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase2.json")
    parser.add_argument(
        "--check-encoder",
        action="store_true",
        help="Re-embed three cached tracklets on CPU with GT/network blocked",
    )
    args = parser.parse_args()
    output = args.output
    # No fallback to downloading, extracting, or recomputing when auditing cache.
    if not (output / "prepared.json").is_file():
        raise FileNotFoundError("Complete the preparation run before this audit")
    saved = json.loads((output / "run.json").read_text())["prediction_sha256"]
    sys.addaudithook(guard)
    repeat = run(config_path=args.config, output=output, verify_only=True)
    assert saved == repeat["prediction_sha256"], "Repeat predictions changed"
    metadata = json.loads((output / "tracklets.json").read_text())
    config = json.loads((output / "config.json").read_text())
    positions = json.loads((output / "topology.json").read_text())["positions"]
    full = json.loads((output / "decisions.json").read_text())
    observations = [
        Observation(**json.loads(line))
        for line in (output / "observations.jsonl").read_text().splitlines()
    ]
    with np.load(output / "embeddings.npz", allow_pickle=False) as saved_features:
        embeddings = dict(
            zip(
                saved_features["keys"].tolist(),
                saved_features["embeddings"],
                strict=True,
            )
        )
    verified_crops = 0
    for track in metadata.values():
        for sample in track["samples"]:
            if sha256(checked_path(output, sample["crop"])) != sample["crop_sha256"]:
                raise ValueError("Evidence crop checksum mismatch")
            verified_crops += 1
    encoder_check = "UNVERIFIED"
    if args.check_encoder:
        from roadeye.embeddings import embed

        selected = {key: metadata[key]["samples"] for key in sorted(metadata)[:3]}
        keys, fresh, model = embed(selected, output, config["embedding"], ROOT)
        assert model["device"] == "cpu"
        expected = np.stack([embeddings[key] for key in keys])
        np.testing.assert_allclose(fresh, expected, rtol=1e-4, atol=1e-5)
        encoder_check = {
            "status": "PASS",
            "tracklets": len(keys),
            "max_absolute_error": float(np.abs(fresh - expected).max()),
        }
    prefix_counts = {}
    for cutoff in (50.0, 100.0, 150.0):
        prefix_meta = {k: v for k, v in metadata.items() if v["ready_s"] <= cutoff}
        prefix_embeddings = {k: embeddings[k] for k in prefix_meta}
        result = associate(
            [o for o in observations if o.time_s <= cutoff],
            prefix_meta,
            prefix_embeddings,
            positions,
            config["association"],
        )
        expected = [d for d in full if d["decision_time_s"] <= cutoff]
        assert result["decisions"] == expected, f"Future leakage at cutoff {cutoff}"
        prefix_counts[str(cutoff)] = len(expected)
    links = json.loads((output / "links.json").read_text())
    for link in links:
        for sample in link["from_appearance_samples"] + link["to_appearance_samples"]:
            assert sample["time_s"] <= link["decision_time_s"]
        assert link["from_evidence"]["time_s"] <= link["decision_time_s"]
    report = {
        "status": "PASS",
        "cached_inference_without_gt_or_network": "PASS",
        "deterministic_prediction_hashes": "PASS",
        "prefix_invariance_decision_counts": prefix_counts,
        "link_evidence_cutoff_checks": len(links),
        "association_seconds": repeat["association_seconds"],
        "evidence_crop_hashes_verified": verified_crops,
        "cpu_encoder_without_gt_or_network": encoder_check,
    }
    write_json(output / "integrity.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
