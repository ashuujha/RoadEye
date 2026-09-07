"""Phase 2 preparation and causal inference. Evaluation is a separate command."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .association import associate, topology
from .embeddings import download_weights, embed
from .tracklets import (
    camera_positions,
    extract_crops,
    load_tracklets,
    sha256,
    write_json,
)

ROOT = Path(__file__).resolve().parents[2]


def configuration(path: Path) -> tuple[dict, dict]:
    config = json.loads(path.read_text(encoding="utf-8"))
    window = json.loads((ROOT / config["window"]).read_text(encoding="utf-8"))
    if set(config["development_scenarios"]) & set(config["evaluation_scenarios"]):
        raise ValueError("Development and evaluation scenarios overlap")
    if window["scenario"] not in config["evaluation_scenarios"]:
        raise ValueError("Run window is not in declared evaluation partition")
    if config["cityflow_training"]:
        raise ValueError("Phase 2 fallback does not train on CityFlow")
    return config, window


def prepare(config_path: Path, output: Path) -> dict:
    config, window = configuration(config_path)
    output.mkdir(parents=True, exist_ok=True)
    root = ROOT / config["dataset_root"]
    tracklets, sources = load_tracklets(root, window)
    positions = camera_positions(root, window)
    weights = ROOT / config["embedding"]["weights"]
    signature = {
        "config_sha256": sha256(config_path),
        "window_sha256": sha256(ROOT / config["window"]),
        "weights_sha256": sha256(weights),
        "sources": sources,
        "positions": positions,
    }
    ready = output / "prepared.json"
    if ready.exists():
        manifest = json.loads(ready.read_text())
        if manifest["input_signature"] != signature:
            raise ValueError("Cache input mismatch; choose a new output directory")
        for name, digest in manifest["artifact_sha256"].items():
            if sha256(output / name) != digest:
                raise ValueError(f"Cache hash mismatch: {name}")
        print("Verified prepared cache reused", flush=True)
        return manifest
    started = time.perf_counter()
    samples, failures = extract_crops(
        root, window, tracklets, output, config["embedding"]["samples_per_tracklet"]
    )
    crop_seconds = time.perf_counter() - started
    started = time.perf_counter()
    keys, matrix, model = embed(samples, output, config["embedding"], ROOT)
    embedding_seconds = time.perf_counter() - started
    np.savez_compressed(
        output / "embeddings.npz", keys=np.array(keys), embeddings=matrix
    )
    metadata = {
        t.key: {
            "key": t.key,
            "partition": t.partition,
            "scenario": t.scenario,
            "camera": t.camera,
            "local_id": t.local_id,
            "ready_s": samples[t.key][-1]["time_s"],
            "samples": samples[t.key],
        }
        for t in tracklets
        if t.key in samples
    }
    write_json(output / "tracklets.json", metadata)
    write_json(output / "config.json", config)
    write_json(output / "window.json", window)
    write_json(output / "topology.json", topology(positions, config["association"]))
    write_json(output / "excluded_tracklets.json", failures)
    with (output / "observations.jsonl").open("w", encoding="utf-8") as stream:
        for tracklet in tracklets:
            for observation in tracklet.observations:
                stream.write(json.dumps(asdict(observation), allow_nan=False) + "\n")
    manifest = {
        "schema_version": 2,
        "input_signature": signature,
        "model": model,
        "baseline_tracklets": len(tracklets),
        "embedded_tracklets": len(keys),
        "baseline_observations": sum(len(t.observations) for t in tracklets),
        "cameras": len(window["cameras"]),
        "prefix_samples": sum(map(len, samples.values())),
        "crop_seconds": crop_seconds,
        "embedding_seconds": embedding_seconds,
        "artifact_sha256": {
            name: sha256(output / name)
            for name in (
                "embeddings.npz",
                "tracklets.json",
                "config.json",
                "window.json",
                "topology.json",
                "observations.jsonl",
                "excluded_tracklets.json",
            )
        },
    }
    write_json(ready, manifest)
    return manifest


def run(
    config_path: Path = ROOT / "configs/phase2.json",
    output: Path = ROOT / "artifacts/phase2-repaired",
) -> dict:
    from .tracklets import Observation

    manifest = prepare(config_path, output)
    config, _ = configuration(config_path)
    metadata = json.loads((output / "tracklets.json").read_text())
    with np.load(output / "embeddings.npz", allow_pickle=False) as stored:
        embeddings = dict(
            zip(stored["keys"].tolist(), stored["embeddings"], strict=True)
        )
    observations = [
        Observation(**json.loads(line))
        for line in (output / "observations.jsonl").read_text().splitlines()
    ]
    started = time.perf_counter()
    result = associate(
        observations,
        metadata,
        embeddings,
        manifest["input_signature"]["positions"],
        config["association"],
    )
    seconds = time.perf_counter() - started
    for name, value in result.items():
        write_json(output / f"{name}.json", value)
    summary = {
        "baseline_tracklets": manifest["baseline_tracklets"],
        "embedded_tracklets": manifest["embedded_tracklets"],
        "assigned_tracklets": len(result["assignments"]),
        "predicted_links": len(result["links"]),
        "global_ids": len(result["journeys"]),
        "max_predicted_camera_coverage": max(
            (j["camera_count"] for j in result["journeys"]), default=0
        ),
        "association_seconds": seconds,
        "prepared_sha256": sha256(output / "prepared.json"),
        "prediction_sha256": {name: sha256(output / f"{name}.json") for name in result},
        "evaluation_status": "not_evaluated_by_runtime",
    }
    write_json(output / "run.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["fetch-weights", "prepare", "run"], default="run", nargs="?"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase2.json")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/phase2-repaired"
    )
    args = parser.parse_args()
    if args.action == "fetch-weights":
        config, _ = configuration(args.config)
        download_weights(ROOT / config["embedding"]["weights"])
    elif args.action == "prepare":
        print(json.dumps(prepare(args.config, args.output), indent=2))
    else:
        run(args.config, args.output)


if __name__ == "__main__":
    main()
