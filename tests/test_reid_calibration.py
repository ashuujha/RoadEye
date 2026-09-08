"""Development-split calibration tests use synthetic identity mappings."""

from scripts.calibrate_trained_association import development_metrics


def test_development_metrics_exclude_training_ids_but_detect_contamination():
    keys = {
        "a": "train/S01/c001/1",
        "b": "train/S01/c002/2",
        "c": "train/S01/c003/3",
        "d": "train/S01/c004/4",
    }
    mapping = {
        keys["a"]: {"identity": "train/S01/dev"},
        keys["b"]: {"identity": "train/S01/dev"},
        keys["c"]: {"identity": "train/S01/training"},
        keys["d"]: {"identity": "train/S01/training"},
    }
    assignments = {
        keys["a"]: "mixed_group",
        keys["b"]: "mixed_group",
        keys["c"]: "mixed_group",
        keys["d"]: "training_only_group",
    }
    links = [
        {"from_key": keys["a"], "to_key": keys["b"]},
        {"from_key": keys["b"], "to_key": keys["c"]},
        {"from_key": keys["c"], "to_key": keys["d"]},
    ]
    metrics = development_metrics(
        mapping, {"train/S01/dev"}, assignments, links
    )
    assert metrics["correct_development_links"] == 1
    assert metrics["incorrect_development_links"] == 1
    assert metrics["ignored_links_without_development_endpoint"] == 1
    assert metrics["development_group_counts"] == {"mixed_gt_identities": 1}
    assert metrics["max_fully_scored_consistent_development_camera_coverage"] == 0
    assert metrics["development_pairwise_precision"] == 1.0
    assert metrics["development_pairwise_recall"] == 1.0


def test_development_metrics_report_unknown_links_separately():
    dev = "train/S01/c001/1"
    unknown = "train/S01/c002/2"
    metrics = development_metrics(
        {dev: {"identity": "train/S01/dev"}, unknown: {"identity": None}},
        {"train/S01/dev"},
        {dev: "group", unknown: "group"},
        [{"from_key": dev, "to_key": unknown}],
    )
    assert metrics["unscored_development_links"] == 1
    assert metrics["development_link_precision"] is None
    assert metrics["status"] == "UNVERIFIED"
