"""Offline evaluator. Only this module reads CityFlow identity annotations."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from .tracklets import Observation, checked_path, sha256, write_json


def box_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if not len(a) or not len(b):
        return np.empty((len(a), len(b)))
    lower = np.maximum(a[:, None, :2], b[None, :, :2])
    upper = np.minimum(a[:, None, :2] + a[:, None, 2:], b[None, :, :2] + b[None, :, 2:])
    intersection = np.prod(np.maximum(0, upper - lower), axis=2)
    union = (
        np.prod(a[:, 2:], axis=1)[:, None]
        + np.prod(b[:, 2:], axis=1)[None, :]
        - intersection
    )
    return intersection / np.maximum(union, 1e-12)


def match_tracks(observations: list[Observation], truth: dict, policy: dict) -> dict:
    """One-to-one per-frame IoU matching followed by coverage/purity checks."""
    frames: dict = defaultdict(list)
    counts: Counter = Counter()
    votes: dict = defaultdict(Counter)
    for observation in observations:
        frames[(observation.camera, observation.frame)].append(observation)
        counts[observation.key] += 1
    for frame, rows in frames.items():
        labels = truth.get(frame, [])
        if not labels:
            continue
        ious = box_iou(
            np.array([r.bbox_xywh for r in rows]), np.array([g[1] for g in labels])
        )
        eligible = ious >= policy["iou_threshold"]
        # Maximize match cardinality before IoU; sub-threshold pairs earn zero.
        weights = np.where(eligible, min(ious.shape) + 1 + ious, 0.0)
        pred_indexes, gt_indexes = linear_sum_assignment(weights, maximize=True)
        for pi, gi in zip(pred_indexes, gt_indexes, strict=True):
            if eligible[pi, gi]:
                votes[rows[pi].key][labels[gi][0]] += 1
    mapping = {}
    for key, count in counts.items():
        matched = sum(votes[key].values())
        identity, majority = votes[key].most_common(1)[0] if matched else (None, 0)
        coverage = matched / count
        purity = majority / matched if matched else 0.0
        usable = (
            matched >= policy["min_matched_observations"]
            and coverage >= policy["min_observation_coverage"]
            and purity >= policy["min_identity_purity"]
        )
        mapping[key] = {
            "identity": identity if usable else None,
            "status": "matched"
            if usable
            else "unmatched"
            if not matched
            else "ambiguous",
            "observations": count,
            "matched_observations": matched,
            "coverage": coverage,
            "purity": purity,
        }
    return mapping


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def association_metrics(mapping: dict, assignments: dict, links: list[dict]) -> dict:
    def identity(key: str) -> str | None:
        return mapping.get(key, {}).get("identity")

    correct = incorrect = unknown = 0
    for link in links:
        a, b = identity(link["from_key"]), identity(link["to_key"])
        if a is None or b is None:
            unknown += 1
        elif a == b:
            correct += 1
        else:
            incorrect += 1
    labeled = sorted(k for k in assignments if identity(k) is not None)
    predicted_pairs = positive_pairs = correct_pairs = 0
    for a, b in combinations(labeled, 2):
        if a.split("/")[:2] != b.split("/")[:2] or a.split("/")[2] == b.split("/")[2]:
            continue
        same_prediction = assignments[a] == assignments[b]
        same_truth = identity(a) == identity(b)
        predicted_pairs += same_prediction
        positive_pairs += same_truth
        correct_pairs += same_prediction and same_truth
    all_truth_groups: dict = defaultdict(Counter)
    for key in mapping:
        label = identity(key)
        if label is not None:
            parts = key.split("/")
            all_truth_groups[(tuple(parts[:2]), label)][parts[2]] += 1
    all_positive_pairs = sum(
        (sum(cameras.values()) ** 2 - sum(n * n for n in cameras.values())) // 2
        for cameras in all_truth_groups.values()
    )
    return {
        "status": "MEASURED" if correct + incorrect else "UNVERIFIED",
        "predicted_links": len(links),
        "evaluable_links": correct + incorrect,
        "correct_links": correct,
        "incorrect_links": incorrect,
        "unscored_links": unknown,
        "link_precision_on_evaluable_links": ratio(correct, correct + incorrect),
        "link_evaluation_coverage": ratio(correct + incorrect, len(links)),
        "all_link_precision_lower_bound": ratio(correct, len(links)),
        "all_link_precision_upper_bound": ratio(correct + unknown, len(links)),
        "labeled_assigned_tracklets": len(labeled),
        "predicted_cross_camera_pairs_on_labeled_tracklets": predicted_pairs,
        "true_cross_camera_pairs_on_labeled_tracklets": positive_pairs,
        "correct_cross_camera_pairs": correct_pairs,
        "pairwise_global_id_precision": ratio(correct_pairs, predicted_pairs),
        "pairwise_global_id_recall": ratio(correct_pairs, positive_pairs),
        "true_cross_camera_pairs_on_all_mappable_tracklets": all_positive_pairs,
        "pairwise_global_id_recall_all_mappable_tracklets": ratio(
            correct_pairs, all_positive_pairs
        ),
    }


def group_quality(mapping: dict, assignments: dict) -> dict:
    groups: dict = defaultdict(list)
    for key, global_id in assignments.items():
        groups[global_id].append(key)
    categories: Counter = Counter()
    maximum = 0
    for keys in groups.values():
        labels = [mapping.get(k, {}).get("identity") for k in keys]
        known = {label for label in labels if label is not None}
        if len(known) > 1:
            categories["mixed_gt_identities"] += 1
        elif not known:
            categories["unscored"] += 1
        elif None in labels:
            categories["partially_scored"] += 1
        else:
            categories["fully_scored_consistent"] += 1
            maximum = max(maximum, len({key.split("/")[2] for key in keys}))
    return {
        "counts": dict(categories),
        "max_fully_scored_consistent_camera_coverage": maximum,
        "scope": "consistency_under_IoU_coverage_purity_mapping_protocol",
    }


def retrieval_metrics(metadata: dict, features: dict, mapping: dict) -> dict:
    """Causal retrieval diagnostic; the gallery excludes unlabelled tracklets."""
    prior = []
    ranks, average_precisions = [], []
    no_positive = 0
    for key in sorted(metadata, key=lambda k: (metadata[k]["ready_s"], k)):
        label = mapping.get(key, {}).get("identity")
        if label is None:
            continue
        gallery = [k for k in prior if metadata[k]["camera"] != metadata[key]["camera"]]
        positives = {k for k in gallery if mapping[k]["identity"] == label}
        if positives:
            ranked = sorted(
                gallery, key=lambda k: (-float(np.dot(features[k], features[key])), k)
            )
            hits = np.array([k in positives for k in ranked])
            ranks.append(bool(hits[0]))
            precisions = np.cumsum(hits) / np.arange(1, len(hits) + 1)
            average_precisions.append(float(np.sum(precisions * hits) / len(positives)))
        else:
            no_positive += 1
        prior.append(key)
    return {
        "queries_with_prior_cross_camera_positive": len(ranks),
        "queries_without_prior_positive": no_positive,
        "rank1_correct": sum(ranks),
        "rank1": ratio(sum(ranks), len(ranks)),
        "map": float(np.mean(average_precisions)) if average_precisions else None,
        "scope": "labeled_gallery_only_at_prefix_ready_time_no_topology_filter",
    }


def evaluate(output: Path, project: Path) -> dict:
    run = json.loads((output / "run.json").read_text())
    prepared = json.loads((output / "prepared.json").read_text())
    if sha256(output / "prepared.json") != run["prepared_sha256"]:
        raise ValueError("Prepared manifest changed after inference")
    for name, digest in prepared["artifact_sha256"].items():
        if sha256(output / name) != digest:
            raise ValueError(f"Prepared input changed: {name}")
    for name, digest in run["prediction_sha256"].items():
        if sha256(output / f"{name}.json") != digest:
            raise ValueError(f"Predictions changed: {name}")
    config = json.loads((output / "config.json").read_text())
    window = json.loads((output / "window.json").read_text())
    role = config.get("run_role", "evaluation")
    if role not in ("development", "evaluation"):
        raise ValueError("Invalid evaluation run role")
    if set(config["development_scenarios"]) & set(config["evaluation_scenarios"]):
        raise ValueError("Development and evaluation scenarios overlap")
    if window["scenario"] not in config[f"{role}_scenarios"]:
        raise ValueError("Scoring scenario does not match declared run role")
    root = project / config["dataset_root"]
    truth: dict = defaultdict(list)
    gt_hashes = {}
    visits = set()
    for camera in window["cameras"]:
        path = checked_path(root, camera["video"]).parent / "gt" / "gt.txt"
        gt_hashes[camera["camera_id"]] = sha256(path)
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                frame = int(row[0])
                timestamp = camera["offset_s"] + (frame - 1) / camera["fps_from_readme"]
                if window["start_s"] <= timestamp <= window["end_s"]:
                    identity = f"{window['partition']}/{window['scenario']}/{row[1]}"
                    truth[(camera["camera_id"], frame)].append(
                        (identity, list(map(float, row[2:6])))
                    )
                    visits.add((identity, camera["camera_id"]))
    observations = [
        Observation(**json.loads(line))
        for line in (output / "observations.jsonl").read_text().splitlines()
    ]
    mapping = match_tracks(observations, truth, config["evaluation"])
    assignments = json.loads((output / "assignments.json").read_text())
    links = json.loads((output / "links.json").read_text())
    metadata = json.loads((output / "tracklets.json").read_text())
    with np.load(output / "embeddings.npz", allow_pickle=False) as stored:
        features = dict(zip(stored["keys"].tolist(), stored["embeddings"], strict=True))
    recovered = {
        (m["identity"], key.split("/")[2])
        for key, m in mapping.items()
        if m["identity"] is not None and key in assignments
    }
    metrics = {
        "scope": config["evaluation_scope"],
        "run_role": role,
        "scenario": window["scenario"],
        "window_start_s": window["start_s"],
        "window_end_s": window["end_s"],
        "baseline_tracklets": len(mapping),
        "baseline_observations": len(observations),
        "mapping_counts": dict(Counter(m["status"] for m in mapping.values())),
        "gt_rows_in_window": sum(map(len, truth.values())),
        "gt_camera_visits": len(visits),
        "recovered_gt_camera_visits": len(recovered & visits),
        "gt_camera_visit_coverage": ratio(len(recovered & visits), len(visits)),
        "association": association_metrics(mapping, assignments, links),
        "group_quality": group_quality(mapping, assignments),
        "appearance_retrieval": retrieval_metrics(metadata, features, mapping),
        "max_predicted_camera_coverage": run["max_predicted_camera_coverage"],
        "global_ids": run["global_ids"],
        "model": prepared["model"],
        "gt_sha256": gt_hashes,
        "run_sha256": sha256(output / "run.json"),
        "evaluation_policy": config["evaluation"],
        "limitations": [
            "Development metrics may select parameters; they are not held-out results"
            if role == "development"
            else config.get(
                "split_limitation",
                "S04 window was selected with labels at feasibility, not an unbiased held-out benchmark",
            ),
            config["threshold_selection"],
            "CityFlow labels are partial; unscored links are unknown, not incorrect",
            prepared["model"]["description"],
            "Baseline MTSC upstream causal behavior and training provenance are not independently audited",
            "Approximate calibration proximity is not a verified road network",
        ],
    }
    write_json(output / "evaluation" / "tracklet_gt_mapping.json", mapping)
    write_json(output / "evaluation" / "metrics.json", metrics)
    print(json.dumps(metrics, indent=2), flush=True)
    return metrics


def main() -> None:
    project = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=project / "artifacts/phase2-repaired"
    )
    args = parser.parse_args()
    evaluate(args.output, project)


if __name__ == "__main__":
    main()
