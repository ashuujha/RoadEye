"""Offline diagnostic: separate pair-level gate losses from appearance failures.

Reads evaluator mappings after predictions exist. Never called by inference and
never changes predictions, thresholds, or the selected experiment configuration.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from roadeye.association import transition
from roadeye.tracklets import Observation, sha256, write_json


def analyze(output: Path) -> dict:
    mapping_path = output / "evaluation/tracklet_gt_mapping.json"
    mapping = json.loads(mapping_path.read_text())
    metadata = json.loads((output / "tracklets.json").read_text())
    config = json.loads((output / "config.json").read_text())
    positions = json.loads((output / "topology.json").read_text())["positions"]
    with np.load(output / "embeddings.npz", allow_pickle=False) as saved:
        features = dict(zip(saved["keys"].tolist(), saved["embeddings"], strict=True))
    rows = [
        Observation(**json.loads(line))
        for line in (output / "observations.jsonl").read_text().splitlines()
    ]
    latest: dict[str, Observation] = {}
    ready = set()
    counts: Counter = Counter()
    positive_rejections: Counter = Counter()
    for current in sorted(rows, key=lambda r: (r.time_s, r.camera, r.frame, r.key)):
        key = current.key
        if key not in metadata or mapping[key]["identity"] is None:
            continue
        latest[key] = current
        if key in ready or current.time_s < metadata[key]["ready_s"]:
            continue
        gallery = [k for k in ready if metadata[k]["camera"] != current.camera]
        positive = {
            k for k in gallery if mapping[k]["identity"] == mapping[key]["identity"]
        }
        if positive:
            counts["queries_with_prior_cross_camera_positive"] += 1
            allowed = []
            for prior in gallery:
                ok, reason, _ = transition(
                    latest[prior], current, positions, config["association"]
                )
                if ok:
                    allowed.append(prior)
                elif prior in positive:
                    positive_rejections[reason] += 1
            if positive.intersection(allowed):
                counts["queries_with_pair_level_admissible_positive"] += 1
                ranked = sorted(
                    allowed,
                    key=lambda k: (-float(np.dot(features[k], features[key])), k),
                )
                counts["correct_rank1_within_labeled_admissible_gallery"] += (
                    ranked[0] in positive
                )
                scores = [
                    float(np.dot(features[k], features[key]))
                    for k in positive.intersection(allowed)
                ]
                counts[
                    "queries_with_admissible_positive_above_similarity_threshold"
                ] += max(scores) >= config["association"]["min_similarity"]
            else:
                counts["queries_losing_all_positives_to_pair_level_gates"] += 1
        ready.add(key)
    report = {
        "status": "MEASURED",
        "run_role": config.get("run_role", "evaluation"),
        "scope": "optimistic pair-level opportunities in labeled gallery; ignores group consistency and unlabeled distractors; not end-to-end accuracy",
        "counts": dict(counts),
        "rejected_positive_pairs_by_reason": dict(positive_rejections),
        "mapping_sha256": sha256(mapping_path),
        "run_sha256": sha256(output / "run.json"),
    }
    write_json(output / "evaluation/error-analysis.json", report)
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    analyze(parser.parse_args().output)


if __name__ == "__main__":
    main()
