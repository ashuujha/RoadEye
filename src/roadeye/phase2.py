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
    text_sha256,
    write_json,
)

ROOT = Path(__file__).resolve().parents[2]


def validate_training_provenance(config: dict) -> dict | None:
    """Validate a CityFlow-trained encoder report without exposing labels at runtime."""
    if not config["cityflow_training"]:
        if config.get("training_provenance"):
            raise ValueError("Untrained configuration declares training provenance")
        return None
    relative = config.get("training_provenance")
    if not relative:
        raise ValueError("CityFlow-trained model requires a provenance report")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Training provenance path escapes the project")
    provenance = json.loads(path.read_text(encoding="utf-8"))
    if provenance.get("status") != "PASS":
        raise ValueError("Training artifact acceptance did not pass")
    training = set(provenance["training_scenarios"])
    evaluation = set(config["evaluation_scenarios"])
    if training != set(config["development_scenarios"]) or training & evaluation:
        raise ValueError("Training/evaluation scenario isolation mismatch")
    if provenance["evaluation_scenarios_used"]:
        raise ValueError("Training provenance declares evaluation scenario use")
    if provenance["weights_sha256"] != config["embedding"].get("weights_sha256"):
        raise ValueError("Runtime model does not match accepted training artifact")
    accepted = set(config.get("accepted_training_limitations", []))
    if (
        provenance["training_python_3_11_status"] != "PASS"
        and "colab_training_python_not_3_11" not in accepted
    ):
        raise ValueError("Training Python deviation was not explicitly accepted")
    if (
        provenance["training_code_archive_linkage_status"] != "PASS"
        and "result_missing_training_code_archive_hash" not in accepted
    ):
        raise ValueError("Training code provenance limitation was not accepted")
    return provenance


def configuration(path: Path) -> tuple[dict, dict]:
    config = json.loads(path.read_text(encoding="utf-8"))
    window = json.loads((ROOT / config["window"]).read_text(encoding="utf-8"))
    if set(config["development_scenarios"]) & set(config["evaluation_scenarios"]):
        raise ValueError("Development and evaluation scenarios overlap")
    role = config.get("run_role", "evaluation")
    if role not in ("development", "evaluation"):
        raise ValueError("Invalid run role")
    if window["scenario"] not in config[f"{role}_scenarios"]:
        raise ValueError(f"Run window is not in declared {role} partition")
    validate_training_provenance(config)
    if config.get("selection_manifest"):
        frozen = json.loads((ROOT / config["selection_manifest"]).read_text())
        if "text_sha256" in frozen:
            checks = {
                ROOT / name: digest for name, digest in frozen["text_sha256"].items()
            }
            for source, digest in checks.items():
                if text_sha256(source) != digest:
                    raise ValueError(f"Frozen experiment changed: {source.name}")
            for name, digest in frozen.get("binary_sha256", {}).items():
                source = ROOT / name
                if sha256(source) != digest:
                    raise ValueError(f"Frozen binary changed: {source.name}")
        else:
            checks = {
                path: frozen["config_sha256"],
                ROOT / config["window"]: frozen["evaluation_window_sha256"],
                ROOT / "configs/reid-experiment.json": frozen["protocol_sha256"],
                ROOT / "reports/reid-development.json": frozen[
                    "development_report_sha256"
                ],
                **{
                    ROOT / name: digest
                    for name, digest in frozen["runtime_source_sha256"].items()
                },
            }
            for source, digest in checks.items():
                if text_sha256(source) != digest:
                    raise ValueError(f"Frozen experiment changed: {source.name}")
    return config, window


def prepare(config_path: Path, output: Path) -> dict:
    config, window = configuration(config_path)
    output.mkdir(parents=True, exist_ok=True)
    root = ROOT / config["dataset_root"]
    tracklets, sources = load_tracklets(
        root, window, config.get("invalid_box_policy", "error")
    )
    positions = camera_positions(root, window)
    weights = ROOT / config["embedding"]["weights"]
    signature = {
        "config_sha256": sha256(config_path),
        "window_sha256": sha256(ROOT / config["window"]),
        "weights_sha256": sha256(weights),
        "sources": sources,
        "positions": positions,
    }
    if config.get("training_provenance"):
        signature["training_provenance_sha256"] = text_sha256(
            ROOT / config["training_provenance"]
        )
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
        root,
        window,
        tracklets,
        output,
        config["embedding"]["samples_per_tracklet"],
        config["embedding"].get("quality_prefix"),
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
            "first_observed_s": t.observations[0].time_s,
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
    verify_only: bool = False,
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
        if verify_only:
            if json.loads((output / f"{name}.json").read_text()) != value:
                raise ValueError(f"Repeat predictions changed: {name}")
        else:
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
    if not verify_only:
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
        download_weights(
            ROOT / config["embedding"]["weights"], config["embedding"]["kind"]
        )
    elif args.action == "prepare":
        print(json.dumps(prepare(args.config, args.output), indent=2))
    else:
        run(args.config, args.output)


if __name__ == "__main__":
    main()
