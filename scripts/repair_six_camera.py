"""Calibrate on S01/S03, freeze, then run one disclosed S04/S05 diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from collections import defaultdict
from copy import deepcopy
from itertools import product
from pathlib import Path

import numpy as np

from roadeye.association import associate
from roadeye.calibration import (
    candidate_is_eligible,
    combine_development_metrics,
    development_metrics,
    selection_key,
)
from roadeye.descriptor_fusion import (
    add_link_similarity_evidence,
    fuse_descriptors,
    tracklet_hsv_descriptors,
)
from roadeye.evaluation import evaluate
from roadeye.phase2 import ROOT, run
from roadeye.reid_training import load_records
from roadeye.tracklets import Observation, sha256, text_sha256, write_json

PROTOCOL = ROOT / "configs/reid-six-camera-repair.json"
PRIVATE_BUNDLE = ROOT / "artifacts/reid-training/data-v2"
DEVELOPMENT = {
    "S01": (
        ROOT / "configs/reid-trained-development.json",
        ROOT / "artifacts/reid-trained-calibration/s01-quality",
    ),
    "S03": (
        ROOT / "configs/reid-trained-development-s03.json",
        ROOT / "artifacts/reid-six-camera-repair/s03-quality",
    ),
}
CALIBRATION_REPORT = ROOT / "reports/reid-six-camera-repair-development.json"
SELECTION_REPORT = ROOT / "reports/reid-six-camera-repair-selection.json"
S04_BASE_CONFIG = ROOT / "configs/reid-six-camera-posthoc-s04-base.json"
POSTHOC_SOURCES = {
    "S04": ROOT / "artifacts/reid-six-camera-repair/s04-trained-base",
    "S05": ROOT / "artifacts/reid-trained-posthoc-s05",
}
POSTHOC_OUTPUTS = {
    scenario: ROOT / f"artifacts/reid-six-camera-repair/posthoc-{scenario.lower()}"
    for scenario in ("S04", "S05")
}
POSTHOC_REPORT = ROOT / "reports/reid-six-camera-repair-posthoc.json"


def _development_identities() -> tuple[dict, dict[str, set[str]]]:
    manifest, records = load_records(PRIVATE_BUNDLE)
    by_scenario = {
        scenario: {
            row["identity"]
            for row in records
            if row["split"] == "development" and row["scenario"] == scenario
        }
        for scenario in DEVELOPMENT
    }
    if {scenario: len(ids) for scenario, ids in by_scenario.items()} != {
        "S01": 19,
        "S03": 4,
    }:
        raise ValueError("Unexpected S01/S03 development identity allocation")
    if any(row["scenario"] in {"S02", "S04", "S05"} for row in records):
        raise ValueError("Evaluation scenario leaked into the private bundle")
    return manifest, by_scenario


def _runtime_inputs(output: Path) -> tuple[list[Observation], dict, dict, dict]:
    metadata = json.loads((output / "tracklets.json").read_text())
    observations = [
        Observation(**json.loads(line))
        for line in (output / "observations.jsonl").read_text().splitlines()
    ]
    positions = json.loads((output / "topology.json").read_text())["positions"]
    with np.load(output / "embeddings.npz", allow_pickle=False) as stored:
        features = dict(
            zip(stored["keys"].tolist(), stored["embeddings"], strict=True)
        )
    return observations, metadata, positions, features


def _prepare_development() -> tuple[dict, dict]:
    initial = {}
    runtime = {}
    for scenario, (config, output) in DEVELOPMENT.items():
        run(config, output)
        initial[scenario] = evaluate(output, ROOT)
        observations, metadata, positions, reid = _runtime_inputs(output)
        runtime[scenario] = {
            "observations": observations,
            "metadata": metadata,
            "positions": positions,
            "reid": reid,
            "hsv": tracklet_hsv_descriptors(output, metadata, (12, 4, 4)),
        }
    return initial, runtime


def calibrate() -> dict:
    if SELECTION_REPORT.exists():
        raise ValueError("Repair selection is already frozen; refusing to recalibrate")
    protocol = json.loads(PROTOCOL.read_text())
    bundle_manifest, identity_sets = _development_identities()
    initial, runtime = _prepare_development()
    mappings = {
        scenario: json.loads(
            (output / "evaluation/tracklet_gt_mapping.json").read_text()
        )
        for scenario, (_, output) in DEVELOPMENT.items()
    }
    candidates = []
    combinations = list(
        product(
            protocol["descriptor"]["hsv_weights"],
            protocol["similarity_grid"],
            protocol["margin_grid"],
            protocol["max_gap_s_grid"],
        )
    )
    fused_by_weight = {
        weight: {
            scenario: fuse_descriptors(row["reid"], row["hsv"], weight)
            for scenario, row in runtime.items()
        }
        for weight in protocol["descriptor"]["hsv_weights"]
    }
    for index, (weight, similarity, margin, max_gap_s) in enumerate(combinations, 1):
        scenario_metrics = {}
        predicted = {}
        for scenario, row in runtime.items():
            base_config = json.loads(DEVELOPMENT[scenario][0].read_text())
            policy = {
                **base_config["association"],
                "min_similarity": similarity,
                "margin": margin,
                "max_gap_s": max_gap_s,
            }
            predictions = associate(
                row["observations"],
                row["metadata"],
                fused_by_weight[weight][scenario],
                row["positions"],
                policy,
            )
            scenario_metrics[scenario] = development_metrics(
                mappings[scenario],
                identity_sets[scenario],
                predictions["assignments"],
                predictions["links"],
            )
            predicted[scenario] = {
                "links": len(predictions["links"]),
                "max_camera_coverage": max(
                    (journey["camera_count"] for journey in predictions["journeys"]),
                    default=0,
                ),
            }
        combined = combine_development_metrics(scenario_metrics)
        candidate = {
            "hsv_weight": weight,
            "policy": policy,
            "scenario_metrics": scenario_metrics,
            "combined_metrics": combined,
            "predicted_all_tracklets": predicted,
        }
        candidate["eligible"] = candidate_is_eligible(
            candidate, protocol["selection"]
        )
        candidates.append(candidate)
        if index % 24 == 0 or index == len(combinations):
            print(
                f"Development sweep {index}/{len(combinations)}; "
                f"eligible={sum(row['eligible'] for row in candidates)}",
                flush=True,
            )
    eligible = sorted(
        (candidate for candidate in candidates if candidate["eligible"]),
        key=selection_key,
    )
    selected = eligible[0] if eligible else None
    report = {
        "status": "PASS" if selected else "FAIL",
        "scope": "S01_S03_identity_disjoint_development_only_association_calibration",
        "not_held_out_accuracy": True,
        "ground_truth_runtime_access": False,
        "protocol_sha256": text_sha256(PROTOCOL),
        "private_bundle_manifest_sha256": sha256(PRIVATE_BUNDLE / "manifest.json"),
        "private_bundle_counts": bundle_manifest["counts"],
        "development_identity_counts": {
            scenario: len(ids) for scenario, ids in identity_sets.items()
        },
        "initial_runtime_and_evaluation_summary": {
            scenario: {
                "baseline_tracklets": row["baseline_tracklets"],
                "mapping_counts": row["mapping_counts"],
                "appearance_retrieval": row["appearance_retrieval"],
            }
            for scenario, row in initial.items()
        },
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected": selected,
        "candidates": candidates,
    }
    write_json(CALIBRATION_REPORT, report)
    _freeze_selection(report)
    print(
        json.dumps({key: value for key, value in report.items() if key != "candidates"}, indent=2),
        flush=True,
    )
    return report


def _freeze_selection(report: dict) -> None:
    selected = report["selected"]
    if selected is None:
        raise ValueError("No development candidate passed; no post-hoc policy frozen")
    tracked_inputs = [
        PROTOCOL,
        CALIBRATION_REPORT,
        S04_BASE_CONFIG,
        ROOT / "configs/reid-trained-development.json",
        ROOT / "configs/reid-trained-development-s03.json",
        ROOT / "configs/reid-development-window.json",
        ROOT / "configs/reid-development-s03-window.json",
        ROOT / "configs/feasibility-window.json",
        ROOT / "configs/reid-evaluation-window.json",
        ROOT / "reports/reid-trained-model.json",
        ROOT / "src/roadeye/association.py",
        ROOT / "src/roadeye/calibration.py",
        ROOT / "src/roadeye/descriptor_fusion.py",
        Path(__file__),
    ]
    development_artifacts = {}
    for scenario, (_, output) in DEVELOPMENT.items():
        for relative in (
            "prepared.json",
            "embeddings.npz",
            "tracklets.json",
            "observations.jsonl",
            "topology.json",
            "evaluation/tracklet_gt_mapping.json",
        ):
            path = output / relative
            development_artifacts[
                f"{scenario}:{path.relative_to(ROOT).as_posix()}"
            ] = sha256(path)
    selection = {
        "status": "PASS",
        "scope": "frozen_S01_S03_development_selection_before_new_S04_S05_predictions",
        "selected_policy": selected["policy"],
        "selected_hsv_weight": selected["hsv_weight"],
        "selected_development_metrics": selected["combined_metrics"],
        "evaluation_labels_opened_by_repair_before_freeze": False,
        "prior_evaluation_state": "S02_S04_S05_already_consumed; all new results must be disclosed post_hoc",
        "tracked_text_sha256": {
            path.relative_to(ROOT).as_posix(): text_sha256(path)
            for path in tracked_inputs
        },
        "development_artifact_sha256": development_artifacts,
        "binary_sha256": {
            "model": json.loads(
                (ROOT / "configs/reid-trained-development.json").read_text()
            )["embedding"]["weights_sha256"]
        },
    }
    write_json(SELECTION_REPORT, selection)


def _verify_selection() -> dict:
    selection = json.loads(SELECTION_REPORT.read_text())
    if selection.get("scope") != (
        "frozen_S01_S03_development_selection_before_new_S04_S05_predictions"
    ):
        raise ValueError("Unexpected six-camera repair selection scope")
    for relative, digest in selection["tracked_text_sha256"].items():
        if text_sha256(ROOT / relative) != digest:
            raise ValueError(f"Frozen repair input changed: {relative}")
    weights = json.loads(
        (ROOT / "configs/reid-trained-development.json").read_text()
    )["embedding"]["weights"]
    if sha256(ROOT / weights) != selection["binary_sha256"]["model"]:
        raise ValueError("Frozen repair model changed")
    return selection


def _verify_prepared_source(output: Path) -> dict:
    prepared = json.loads((output / "prepared.json").read_text())
    for relative, digest in prepared["artifact_sha256"].items():
        if sha256(output / relative) != digest:
            raise ValueError(f"Prepared source changed: {output.name}/{relative}")
    if prepared["model"]["weights_sha256"] != json.loads(
        SELECTION_REPORT.read_text()
    )["binary_sha256"]["model"]:
        raise ValueError("Prepared source uses a different Re-ID model")
    return prepared


def _materialize_posthoc(
    scenario: str, source: Path, output: Path, selection: dict
) -> dict:
    prepared = _verify_prepared_source(source)
    observations, metadata, positions, reid = _runtime_inputs(source)
    hsv = tracklet_hsv_descriptors(source, metadata, (12, 4, 4))
    weight = selection["selected_hsv_weight"]
    fused = fuse_descriptors(reid, hsv, weight)
    output.mkdir(parents=True, exist_ok=True)
    for relative in (
        "tracklets.json",
        "observations.jsonl",
        "topology.json",
        "window.json",
        "excluded_tracklets.json",
    ):
        shutil.copyfile(source / relative, output / relative)
    base_config = json.loads((source / "config.json").read_text())
    config = deepcopy(base_config)
    config.pop("selection_manifest", None)
    config.update(
        {
            "run_role": "evaluation",
            "evaluation_scope": f"{scenario}_consumed_post_hoc_after_S01_S03_development_repair",
            "threshold_selection": "S01/S03 development-only descriptor and association freeze before new S04/S05 predictions",
            "split_limitation": f"{scenario} was already consumed; this is post-hoc diagnostic evidence, not a fresh held-out result",
            "association": selection["selected_policy"],
            "descriptor_fusion": {
                "kind": "weighted_concatenation_of_unit_reid_and_causal_hsv_prefix",
                "hsv_bins": [12, 4, 4],
                "hsv_weight": weight,
                "selection_manifest": SELECTION_REPORT.relative_to(ROOT).as_posix(),
            },
        }
    )
    write_json(output / "config.json", config)
    np.savez_compressed(
        output / "embeddings.npz",
        keys=np.array(sorted(fused)),
        embeddings=np.stack([fused[key] for key in sorted(fused)]),
    )
    model = deepcopy(prepared["model"])
    model.update(
        {
            "dimensions": len(next(iter(fused.values()))),
            "descriptor_fusion": config["descriptor_fusion"],
            "description": (
                prepared["model"]["description"]
                + "; fused with a development-selected causal HSV prefix histogram"
            ),
            "evidence_crop_artifact_root": source.relative_to(ROOT).as_posix(),
        }
    )
    artifact_names = (
        "embeddings.npz",
        "tracklets.json",
        "config.json",
        "window.json",
        "topology.json",
        "observations.jsonl",
        "excluded_tracklets.json",
    )
    derived_prepared = {
        "schema_version": 2,
        "input_signature": {
            **prepared["input_signature"],
            "config_sha256": sha256(output / "config.json"),
            "repair_selection_sha256": sha256(SELECTION_REPORT),
            "source_prepared_sha256": sha256(source / "prepared.json"),
        },
        "model": model,
        "baseline_tracklets": prepared["baseline_tracklets"],
        "embedded_tracklets": prepared["embedded_tracklets"],
        "baseline_observations": prepared["baseline_observations"],
        "cameras": prepared["cameras"],
        "prefix_samples": prepared["prefix_samples"],
        "crop_seconds": 0.0,
        "embedding_seconds": 0.0,
        "derivation": "hash_verified_existing_CPU_ReID_plus_causal_HSV_fusion",
        "artifact_sha256": {
            relative: sha256(output / relative) for relative in artifact_names
        },
    }
    write_json(output / "prepared.json", derived_prepared)
    started = time.perf_counter()
    raw_predictions = associate(
        observations,
        metadata,
        fused,
        positions,
        selection["selected_policy"],
    )
    predictions = add_link_similarity_evidence(
        raw_predictions,
        reid,
        hsv,
        weight,
        source.relative_to(ROOT).as_posix(),
    )
    for name, value in predictions.items():
        write_json(output / f"{name}.json", value)
    summary = {
        "baseline_tracklets": prepared["baseline_tracklets"],
        "embedded_tracklets": prepared["embedded_tracklets"],
        "assigned_tracklets": len(predictions["assignments"]),
        "predicted_links": len(predictions["links"]),
        "global_ids": len(predictions["journeys"]),
        "max_predicted_camera_coverage": max(
            (row["camera_count"] for row in predictions["journeys"]), default=0
        ),
        "association_seconds": time.perf_counter() - started,
        "prepared_sha256": sha256(output / "prepared.json"),
        "prediction_sha256": {
            name: sha256(output / f"{name}.json") for name in predictions
        },
        "evaluation_status": "not_evaluated_by_runtime",
        "selection_sha256": sha256(SELECTION_REPORT),
    }
    write_json(output / "run.json", summary)
    print(json.dumps({"scenario": scenario, **summary}, indent=2), flush=True)
    return summary


def _verified_journey_details(output: Path) -> dict:
    mapping = json.loads(
        (output / "evaluation/tracklet_gt_mapping.json").read_text()
    )
    assignments = json.loads((output / "assignments.json").read_text())
    groups: dict[str, list[str]] = defaultdict(list)
    for key, global_id in assignments.items():
        groups[global_id].append(key)
    consistent = []
    for global_id, keys in groups.items():
        labels = [mapping.get(key, {}).get("identity") for key in keys]
        if None in labels or len(set(labels)) != 1:
            continue
        cameras = sorted({key.split("/")[2] for key in keys})
        consistent.append(
            {
                "roadeye_global_id": global_id,
                "camera_count": len(cameras),
                "cameras": cameras,
                "tracklet_count": len(keys),
                "gt_identity_sha256_prefix": hashlib.sha256(
                    labels[0].encode()
                ).hexdigest()[:16],
            }
        )
    consistent.sort(key=lambda row: (-row["camera_count"], row["roadeye_global_id"]))
    return {
        "max_fully_scored_consistent_camera_coverage": (
            consistent[0]["camera_count"] if consistent else 0
        ),
        "best_fully_scored_consistent_journeys": consistent[:5],
    }


def posthoc() -> dict:
    selection = _verify_selection()
    run(S04_BASE_CONFIG, POSTHOC_SOURCES["S04"])
    runtime = {
        scenario: _materialize_posthoc(
            scenario, POSTHOC_SOURCES[scenario], POSTHOC_OUTPUTS[scenario], selection
        )
        for scenario in ("S04", "S05")
    }
    metrics = {
        scenario: evaluate(POSTHOC_OUTPUTS[scenario], ROOT)
        for scenario in ("S04", "S05")
    }
    verified = {
        scenario: _verified_journey_details(POSTHOC_OUTPUTS[scenario])
        for scenario in ("S04", "S05")
    }
    maximum = max(
        row["max_fully_scored_consistent_camera_coverage"]
        for row in verified.values()
    )
    report = {
        "status": "PASS" if maximum >= 6 else "FAIL",
        "scope": "single_disclosed_S04_S05_post_hoc_six_camera_repair_diagnostic",
        "held_out_status": "POST_HOC_NOT_HELD_OUT",
        "selection_sha256": sha256(SELECTION_REPORT),
        "selected_policy": selection["selected_policy"],
        "selected_hsv_weight": selection["selected_hsv_weight"],
        "predictions_written_for_both_scenarios_before_evaluation": True,
        "runtime_ground_truth_access": False,
        "maximum_fully_scored_consistent_camera_coverage": maximum,
        "six_camera_criterion": "PASS" if maximum >= 6 else "FAIL",
        "runtime": runtime,
        "metrics": metrics,
        "verified_journeys": verified,
        "demo_claim": (
            "post_hoc_six_camera_prediction_available_but_not_fresh_held_out"
            if maximum >= 6
            else "retain_frozen_S02_demo_and_two_camera_verified_maximum"
        ),
    }
    write_json(POSTHOC_REPORT, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "six_camera_criterion": report["six_camera_criterion"],
                "maximum_fully_scored_consistent_camera_coverage": maximum,
                "per_scenario": {
                    scenario: {
                        "max_predicted_camera_coverage": runtime[scenario][
                            "max_predicted_camera_coverage"
                        ],
                        **verified[scenario],
                    }
                    for scenario in ("S04", "S05")
                },
            },
            indent=2,
        ),
        flush=True,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["calibrate", "posthoc"])
    args = parser.parse_args()
    if args.action == "calibrate":
        calibrate()
    else:
        posthoc()


if __name__ == "__main__":
    main()
