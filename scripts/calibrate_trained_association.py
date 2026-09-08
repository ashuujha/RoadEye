"""Calibrate association on private S01 development IDs, then freeze S05 post-hoc."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations, product
from pathlib import Path

import numpy as np

from roadeye.association import associate
from roadeye.evaluation import evaluate, ratio
from roadeye.phase2 import ROOT, run
from roadeye.reid_training import load_records
from roadeye.tracklets import Observation, sha256, text_sha256, write_json

PROTOCOL = ROOT / "configs/reid-trained-calibration.json"
DEVELOPMENT_CONFIG = ROOT / "configs/reid-trained-development.json"
DEVELOPMENT_OUTPUT = ROOT / "artifacts/reid-trained-calibration/s01-quality"
PRIVATE_BUNDLE = ROOT / "artifacts/reid-training/data-v2"
CALIBRATION_REPORT = ROOT / "reports/reid-trained-association-calibration.json"
POSTHOC_CONFIG = ROOT / "configs/reid-trained-posthoc-s05.json"
SELECTION_REPORT = ROOT / "reports/reid-trained-association-selection.json"
POSTHOC_OUTPUT = ROOT / "artifacts/reid-trained-posthoc-s05"


def _development_identities() -> tuple[dict, set[str]]:
    manifest, records = load_records(PRIVATE_BUNDLE)
    identities = {
        row["identity"]
        for row in records
        if row["split"] == "development" and row["scenario"] == "S01"
    }
    if len(identities) != 19:
        raise ValueError("Unexpected S01 development identity count")
    if any(row["scenario"] in {"S02", "S04", "S05"} for row in records):
        raise ValueError("Evaluation scenario leaked into the private bundle")
    return manifest, identities


def development_metrics(
    mapping: dict,
    development_identities: set[str],
    assignments: dict[str, str],
    links: list[dict],
) -> dict:
    """Score only identity-disjoint development IDs while retaining distractors."""

    def identity(key: str) -> str | None:
        return mapping.get(key, {}).get("identity")

    development_keys = {
        key for key in assignments if identity(key) in development_identities
    }
    correct = incorrect = unknown = ignored = 0
    for link in links:
        source, target = link["from_key"], link["to_key"]
        if source not in development_keys and target not in development_keys:
            ignored += 1
            continue
        source_id, target_id = identity(source), identity(target)
        if source_id is None or target_id is None:
            unknown += 1
        elif source_id == target_id:
            correct += 1
        else:
            incorrect += 1

    predicted_pairs = true_pairs = correct_pairs = 0
    for source, target in combinations(sorted(development_keys), 2):
        if source.split("/")[2] == target.split("/")[2]:
            continue
        same_prediction = assignments[source] == assignments[target]
        same_identity = identity(source) == identity(target)
        predicted_pairs += same_prediction
        true_pairs += same_identity
        correct_pairs += same_prediction and same_identity

    groups: dict[str, list[str]] = defaultdict(list)
    for key, global_id in assignments.items():
        groups[global_id].append(key)
    group_counts: Counter = Counter()
    max_consistent_cameras = 0
    for keys in groups.values():
        if not development_keys.intersection(keys):
            continue
        labels = [identity(key) for key in keys]
        known = {label for label in labels if label is not None}
        if len(known) > 1:
            group_counts["mixed_gt_identities"] += 1
        elif None in labels:
            group_counts["partially_scored"] += 1
        elif known and next(iter(known)) in development_identities:
            group_counts["fully_scored_consistent"] += 1
            max_consistent_cameras = max(
                max_consistent_cameras, len({key.split("/")[2] for key in keys})
            )

    precision = ratio(correct_pairs, predicted_pairs)
    recall = ratio(correct_pairs, true_pairs)
    pairwise_f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
    )
    return {
        "status": "MEASURED" if correct + incorrect else "UNVERIFIED",
        "development_identities": len(development_identities),
        "mapped_development_tracklets": len(development_keys),
        "relevant_predicted_links": correct + incorrect + unknown,
        "evaluable_development_links": correct + incorrect,
        "correct_development_links": correct,
        "incorrect_development_links": incorrect,
        "unscored_development_links": unknown,
        "ignored_links_without_development_endpoint": ignored,
        "development_link_precision": ratio(correct, correct + incorrect),
        "development_link_evaluation_coverage": ratio(
            correct + incorrect, correct + incorrect + unknown
        ),
        "predicted_development_cross_camera_pairs": predicted_pairs,
        "true_development_cross_camera_pairs": true_pairs,
        "correct_development_cross_camera_pairs": correct_pairs,
        "development_pairwise_precision": precision,
        "development_pairwise_recall": recall,
        "development_pairwise_f1": pairwise_f1,
        "development_group_counts": dict(group_counts),
        "max_fully_scored_consistent_development_camera_coverage": (
            max_consistent_cameras
        ),
    }


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


def calibrate() -> dict:
    protocol = json.loads(PROTOCOL.read_text())
    config = json.loads(DEVELOPMENT_CONFIG.read_text())
    bundle_manifest, development_ids = _development_identities()
    run(DEVELOPMENT_CONFIG, DEVELOPMENT_OUTPUT)
    initial = evaluate(DEVELOPMENT_OUTPUT, ROOT)
    mapping = json.loads(
        (DEVELOPMENT_OUTPUT / "evaluation/tracklet_gt_mapping.json").read_text()
    )
    observations, metadata, positions, features = _runtime_inputs(DEVELOPMENT_OUTPUT)
    candidates = []
    for similarity, margin, max_gap_s in product(
        protocol["similarity_grid"],
        protocol["margin_grid"],
        protocol["max_gap_s_grid"],
    ):
        policy = {
            **config["association"],
            "min_similarity": similarity,
            "margin": margin,
            "max_gap_s": max_gap_s,
        }
        predictions = associate(observations, metadata, features, positions, policy)
        metrics = development_metrics(
            mapping, development_ids, predictions["assignments"], predictions["links"]
        )
        gate = protocol["selection"]
        eligible = (
            metrics["evaluable_development_links"]
            >= gate["minimum_evaluable_development_links"]
            and metrics["development_link_precision"] is not None
            and metrics["development_link_precision"]
            >= gate["minimum_development_link_precision"]
        )
        candidates.append(
            {
                "policy": policy,
                "metrics": metrics,
                "eligible": eligible,
                "predicted_links_all_tracklets": len(predictions["links"]),
                "max_predicted_camera_coverage_all_tracklets": max(
                    (row["camera_count"] for row in predictions["journeys"]),
                    default=0,
                ),
            }
        )
        print(
            "DEV "
            f"sim={similarity:.2f} margin={margin:.2f} gap={max_gap_s:.0f}: "
            f"links={metrics['correct_development_links']}/"
            f"{metrics['evaluable_development_links']} "
            f"F1={metrics['development_pairwise_f1']:.4f} "
            f"span={metrics['max_fully_scored_consistent_development_camera_coverage']} "
            f"eligible={eligible}",
            flush=True,
        )

    eligible = [row for row in candidates if row["eligible"]]
    eligible.sort(
        key=lambda row: (
            -row["metrics"]["development_pairwise_f1"],
            -row["metrics"][
                "max_fully_scored_consistent_development_camera_coverage"
            ],
            row["metrics"]["development_group_counts"].get(
                "mixed_gt_identities", 0
            ),
            -row["metrics"]["development_link_precision"],
            -row["policy"]["min_similarity"],
            -row["policy"]["margin"],
            row["policy"]["max_gap_s"],
        )
    )
    selected = eligible[0] if eligible else None
    report = {
        "status": "PASS" if selected else "FAIL",
        "scope": "S01_identity_disjoint_development_association_calibration",
        "not_held_out_accuracy": True,
        "protocol_sha256": text_sha256(PROTOCOL),
        "development_config_sha256": text_sha256(DEVELOPMENT_CONFIG),
        "private_bundle_manifest_sha256": sha256(PRIVATE_BUNDLE / "manifest.json"),
        "private_bundle_counts": bundle_manifest["counts"],
        "trained_weights_sha256": config["embedding"]["weights_sha256"],
        "development_identity_count": len(development_ids),
        "initial_all_identity_evaluator_summary": {
            "mapping_counts": initial["mapping_counts"],
            "appearance_retrieval": initial["appearance_retrieval"],
        },
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected": selected,
        "candidates": candidates,
    }
    write_json(CALIBRATION_REPORT, report)
    _freeze_posthoc(config, selected, report)
    print(json.dumps({key: value for key, value in report.items() if key != "candidates"}, indent=2))
    return report


def _freeze_posthoc(base: dict, selected: dict | None, report: dict) -> None:
    config = deepcopy(base)
    if selected:
        config["association"] = selected["policy"]
    config.update(
        {
            "window": "configs/reid-evaluation-window.json",
            "evaluation_scope": "S05_consumed_post_hoc_after_S01_development_only_calibration",
            "run_role": "evaluation",
            "threshold_selection": (
                "S01 identity-disjoint development calibration; S05 already consumed and post-hoc"
                if selected
                else "No S01 candidate passed the calibration gate; retained original thresholds for post-hoc diagnostic"
            ),
            "split_limitation": (
                "S05 is consumed and was previously inspected; this is a disclosed post-hoc diagnostic, never fresh held-out evidence"
            ),
            "selection_manifest": "reports/reid-trained-association-selection.json",
            "invalid_box_policy": "exclude_nonpositive_and_record",
        }
    )
    write_json(POSTHOC_CONFIG, config)
    selection = {
        "status": report["status"],
        "scope": "freeze_S01_selected_policy_before_S05_post_hoc_predictions",
        "evaluation_labels_opened_by_this_script_before_freeze": False,
        "s05_prior_state": "consumed_before_this_checkpoint",
        "selected_policy": config["association"],
        "text_sha256": {
            path.relative_to(ROOT).as_posix(): text_sha256(path)
            for path in [
                POSTHOC_CONFIG,
                ROOT / "configs/reid-evaluation-window.json",
                PROTOCOL,
                CALIBRATION_REPORT,
                ROOT / "reports/reid-trained-model.json",
                *sorted((ROOT / "src/roadeye").glob("*.py")),
            ]
        },
        "binary_sha256": {
            config["embedding"]["weights"]: config["embedding"]["weights_sha256"]
        },
    }
    write_json(SELECTION_REPORT, selection)


def posthoc() -> dict:
    selection = json.loads(SELECTION_REPORT.read_text())
    if selection["scope"] != "freeze_S01_selected_policy_before_S05_post_hoc_predictions":
        raise ValueError("Unexpected selection manifest")
    run(POSTHOC_CONFIG, POSTHOC_OUTPUT)
    metrics = evaluate(POSTHOC_OUTPUT, ROOT)
    write_json(ROOT / "reports/reid-trained-posthoc-s05-metrics.json", metrics)
    return metrics


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
