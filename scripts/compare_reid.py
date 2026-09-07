"""Bounded development comparison and parameter freeze; never score S05 here."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product

import numpy as np

from roadeye.association import associate
from roadeye.evaluation import association_metrics, evaluate, group_quality
from roadeye.phase2 import ROOT, run
from roadeye.tracklets import Observation, sha256, text_sha256, write_json

PROTOCOL = ROOT / "configs/reid-experiment.json"


def initialize() -> None:
    protocol = json.loads(PROTOCOL.read_text())
    base = json.loads((ROOT / "configs/phase2.json").read_text())
    for variant in protocol["variants"]:
        config = deepcopy(base)
        config.update(
            {
                "run_role": "development",
                "development_scenarios": ["S01"],
                "evaluation_scenarios": ["S04", "S05"],
                "window": "configs/reid-development-window.json",
                "evaluation_scope": "S01_clock_selected_development_not_held_out",
                "threshold_selection": "initial policy before predeclared S01 grid",
            }
        )
        if variant.startswith("veri"):
            config["embedding"].update(
                {
                    "kind": "fastreid_veri_sbs_r50_ibn",
                    "weights": "artifacts/models/veri_sbs_R50-ibn.pth",
                    "batch_size": 8,
                }
            )
        if variant == "veri_quality":
            config["embedding"]["quality_prefix"] = protocol["quality_prefix"]
        path = ROOT / f"configs/reid-dev-{variant}.json"
        if path.exists() and json.loads(path.read_text()) != config:
            raise ValueError("Refusing to change existing development configuration")
        write_json(path, config)


def develop(variant: str) -> None:
    protocol = json.loads(PROTOCOL.read_text())
    if variant not in protocol["variants"]:
        raise ValueError("Variant not predeclared")
    output = ROOT / f"artifacts/reid-development/{variant}"
    config_path = ROOT / f"configs/reid-dev-{variant}.json"
    config = json.loads(config_path.read_text())
    if (
        config["run_role"] != "development"
        or config["window"] != "configs/reid-development-window.json"
    ):
        raise ValueError("This comparison may access only the development window")
    run(config_path, output)
    initial = evaluate(output, ROOT)
    mapping = json.loads((output / "evaluation/tracklet_gt_mapping.json").read_text())
    metadata = json.loads((output / "tracklets.json").read_text())
    observations = [
        Observation(**json.loads(line))
        for line in (output / "observations.jsonl").read_text().splitlines()
    ]
    positions = json.loads((output / "topology.json").read_text())["positions"]
    with np.load(output / "embeddings.npz", allow_pickle=False) as arrays:
        features = dict(zip(arrays["keys"].tolist(), arrays["embeddings"], strict=True))
    comparisons = []
    for similarity, margin in product(
        protocol["development_similarity_grid"], protocol["development_margin_grid"]
    ):
        policy = {
            **config["association"],
            "min_similarity": similarity,
            "margin": margin,
        }
        predictions = associate(observations, metadata, features, positions, policy)
        metrics = association_metrics(
            mapping, predictions["assignments"], predictions["links"]
        )
        precision, recall = (
            metrics["pairwise_global_id_precision"],
            metrics["pairwise_global_id_recall_all_mappable_tracklets"],
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else 0.0
        )
        eligible = (
            metrics["evaluable_links"]
            >= protocol["selection"]["minimum_evaluable_links"]
            and metrics["link_precision_on_evaluable_links"] is not None
            and metrics["link_precision_on_evaluable_links"]
            >= protocol["selection"]["minimum_link_precision"]
        )
        name = f"similarity-{similarity}_margin-{margin}.json"
        path = output / "development-grid" / name
        write_json(
            path,
            {
                "policy": policy,
                "assignments": predictions["assignments"],
                "links": predictions["links"],
            },
        )
        comparisons.append(
            {
                "variant": variant,
                "policy": policy,
                "metrics": metrics,
                "pairwise_f1": f1,
                "eligible": eligible,
                "group_quality": group_quality(mapping, predictions["assignments"]),
                "prediction_file": path.relative_to(ROOT).as_posix(),
                "prediction_sha256": sha256(path),
            }
        )
        print(
            f"DEV {variant} similarity={similarity} margin={margin}: {metrics['correct_links']}/{metrics['evaluable_links']} links, F1={f1:.4f}, eligible={eligible}",
            flush=True,
        )
    write_json(
        output / "comparison.json",
        {
            "initial": initial,
            "grid": comparisons,
            "protocol_sha256": text_sha256(PROTOCOL),
        },
    )


def select() -> None:
    protocol = json.loads(PROTOCOL.read_text())
    reports = {}
    for variant in protocol["variants"]:
        path = ROOT / f"artifacts/reid-development/{variant}/comparison.json"
        report = json.loads(path.read_text())
        if report["protocol_sha256"] != text_sha256(PROTOCOL):
            raise ValueError("Development protocol changed")
        for candidate in report["grid"]:
            if (
                sha256(ROOT / candidate["prediction_file"])
                != candidate["prediction_sha256"]
            ):
                raise ValueError("Development predictions changed")
        reports[variant] = report
    candidates = [
        candidate
        for report in reports.values()
        for candidate in report["grid"]
        if candidate["eligible"]
    ]
    candidates.sort(
        key=lambda c: (
            -c["pairwise_f1"],
            -c["metrics"]["link_precision_on_evaluable_links"],
            -c["policy"]["min_similarity"],
            c["variant"],
            c["policy"]["margin"],
        )
    )
    choice = candidates[0] if candidates else None
    variant = choice["variant"] if choice else "imagenet_prefix"
    config = json.loads((ROOT / f"configs/reid-dev-{variant}.json").read_text())
    if choice:
        config["association"] = choice["policy"]
    config.update(
        {
            "run_role": "evaluation",
            "window": "configs/reid-evaluation-window.json",
            "evaluation_scope": "S05_clock_selected_evaluation_after_S01_development",
            "threshold_selection": "predeclared S01 development grid; frozen before S05 scoring",
            "split_limitation": "S05 shares locations/cameras with previously inspected S04; no novel-site or verified novel-identity generalization claim",
            "selection_manifest": "reports/reid-selection.json",
            "invalid_box_policy": "exclude_nonpositive_and_record",
        }
    )
    config_path = ROOT / "configs/reid-evaluation.json"
    freeze_path = ROOT / "reports/reid-selection.json"
    if freeze_path.exists():
        raise ValueError("Selection already frozen; do not replace after evaluation")
    write_json(config_path, config)
    write_json(ROOT / "reports/reid-development.json", reports)
    freeze = {
        "selected_at_utc": datetime.now(timezone.utc).isoformat(),
        "text_hash_rule": "SHA256 of UTF-8 file bytes with CRLF normalized to LF",
        "protocol_sha256": text_sha256(PROTOCOL),
        "config_sha256": text_sha256(config_path),
        "evaluation_window_sha256": text_sha256(ROOT / config["window"]),
        "development_report_sha256": text_sha256(
            ROOT / "reports/reid-development.json"
        ),
        "runtime_source_sha256": {
            p.relative_to(ROOT).as_posix(): text_sha256(p)
            for p in sorted((ROOT / "src/roadeye").glob("*.py"))
        },
        "selected_variant": variant,
        "qualified_improvement": choice is not None,
        "selected_development_result": choice,
        "evaluation_labels_opened_by_this_experiment_at_freeze": False,
        "scope": "development selection only; S05 metrics do not exist yet",
    }
    write_json(freeze_path, freeze)
    print(json.dumps(freeze, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["initialize", "develop", "select"])
    parser.add_argument(
        "--variant", choices=["imagenet_prefix", "veri_prefix", "veri_quality"]
    )
    args = parser.parse_args()
    if args.action == "initialize":
        initialize()
    elif args.action == "develop":
        if not args.variant:
            parser.error("develop requires --variant")
        develop(args.variant)
    else:
        select()


if __name__ == "__main__":
    main()
