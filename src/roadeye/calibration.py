"""Development-only association measurements and deterministic selection."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from .evaluation import ratio


def development_metrics(
    mapping: dict,
    development_identities: set[str],
    assignments: dict[str, str],
    links: list[dict],
) -> dict:
    """Score selected development IDs while retaining every runtime distractor."""

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
    group_counts: Counter[str] = Counter()
    maximum = 0
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
            maximum = max(maximum, len({key.split("/")[2] for key in keys}))

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
        "max_fully_scored_consistent_development_camera_coverage": maximum,
    }


def combine_development_metrics(by_scenario: dict[str, dict]) -> dict:
    """Aggregate independent scenarios without creating cross-scenario pairs."""

    additive = (
        "development_identities",
        "mapped_development_tracklets",
        "relevant_predicted_links",
        "evaluable_development_links",
        "correct_development_links",
        "incorrect_development_links",
        "unscored_development_links",
        "ignored_links_without_development_endpoint",
        "predicted_development_cross_camera_pairs",
        "true_development_cross_camera_pairs",
        "correct_development_cross_camera_pairs",
    )
    result = {name: sum(row[name] for row in by_scenario.values()) for name in additive}
    groups: Counter[str] = Counter()
    for row in by_scenario.values():
        groups.update(row["development_group_counts"])
    link_precision = ratio(
        result["correct_development_links"], result["evaluable_development_links"]
    )
    pairwise_precision = ratio(
        result["correct_development_cross_camera_pairs"],
        result["predicted_development_cross_camera_pairs"],
    )
    pairwise_recall = ratio(
        result["correct_development_cross_camera_pairs"],
        result["true_development_cross_camera_pairs"],
    )
    result.update(
        {
            "status": (
                "MEASURED"
                if result["evaluable_development_links"]
                else "UNVERIFIED"
            ),
            "development_link_precision": link_precision,
            "development_link_evaluation_coverage": ratio(
                result["evaluable_development_links"],
                result["relevant_predicted_links"],
            ),
            "development_pairwise_precision": pairwise_precision,
            "development_pairwise_recall": pairwise_recall,
            "development_pairwise_f1": (
                2
                * pairwise_precision
                * pairwise_recall
                / (pairwise_precision + pairwise_recall)
                if pairwise_precision is not None
                and pairwise_recall is not None
                and pairwise_precision + pairwise_recall
                else 0.0
            ),
            "development_group_counts": dict(groups),
            "max_fully_scored_consistent_development_camera_coverage": max(
                (
                    row[
                        "max_fully_scored_consistent_development_camera_coverage"
                    ]
                    for row in by_scenario.values()
                ),
                default=0,
            ),
        }
    )
    return result


def candidate_is_eligible(candidate: dict, gate: dict) -> bool:
    combined = candidate["combined_metrics"]
    if (
        combined["evaluable_development_links"]
        < gate["minimum_evaluable_development_links"]
        or combined["development_link_precision"] is None
        or combined["development_link_precision"]
        < gate["minimum_development_link_precision"]
    ):
        return False
    return all(
        row["evaluable_development_links"]
        >= gate["minimum_evaluable_links_per_scenario"]
        and row["development_link_precision"] is not None
        and row["development_link_precision"]
        >= gate["minimum_link_precision_per_scenario"]
        for row in candidate["scenario_metrics"].values()
    )


def selection_key(candidate: dict) -> tuple:
    metrics = candidate["combined_metrics"]
    s03 = candidate["scenario_metrics"]["S03"]
    return (
        -metrics["max_fully_scored_consistent_development_camera_coverage"],
        -metrics["development_pairwise_f1"],
        -s03["development_pairwise_f1"],
        metrics["development_group_counts"].get("mixed_gt_identities", 0),
        -metrics["development_link_precision"],
        -candidate["policy"]["min_similarity"],
        -candidate["policy"]["margin"],
        candidate["policy"]["max_gap_s"],
        candidate["hsv_weight"],
    )
