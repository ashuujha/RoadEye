"""Returned Re-ID artifact policy tests use synthetic manifests only."""

from __future__ import annotations

import json

import pytest

from roadeye.phase2 import configuration
from roadeye.tracklets import sha256, text_sha256, write_json
from scripts.verify_reid_result import _safe_members


def test_returned_archive_member_policy_rejects_path_escape():
    assert _safe_members(
        ["history.json", "roadeye_cityflow_reid.json", "roadeye_cityflow_reid.pt"]
    )
    assert not _safe_members(["../roadeye_cityflow_reid.pt"])
    assert not _safe_members(["folder\\roadeye_cityflow_reid.pt"])


def test_trained_runtime_requires_isolated_provenance_and_explicit_limitations(
    tmp_path, monkeypatch
):
    from roadeye import phase2

    monkeypatch.setattr(phase2, "ROOT", tmp_path)
    write_json(tmp_path / "window.json", {"scenario": "S02"})
    provenance = {
        "status": "PASS",
        "training_scenarios": ["S01", "S03"],
        "evaluation_scenarios_used": [],
        "weights_sha256": "a" * 64,
        "training_python_3_11_status": "FAIL",
        "training_code_archive_linkage_status": "UNVERIFIED",
    }
    write_json(tmp_path / "provenance.json", provenance)
    config = {
        "window": "window.json",
        "run_role": "evaluation",
        "cityflow_training": True,
        "training_provenance": "provenance.json",
        "development_scenarios": ["S01", "S03"],
        "evaluation_scenarios": ["S02"],
        "embedding": {"weights_sha256": "a" * 64},
        "accepted_training_limitations": [
            "colab_training_python_not_3_11",
            "result_missing_training_code_archive_hash",
        ],
    }
    config_path = tmp_path / "config.json"
    write_json(config_path, config)
    assert configuration(config_path)[1]["scenario"] == "S02"

    provenance["evaluation_scenarios_used"] = ["S02"]
    write_json(tmp_path / "provenance.json", provenance)
    with pytest.raises(ValueError, match="evaluation scenario use"):
        configuration(config_path)

    provenance["evaluation_scenarios_used"] = []
    write_json(tmp_path / "provenance.json", provenance)
    config["accepted_training_limitations"] = []
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="Python deviation"):
        configuration(config_path)


def test_generic_freeze_rejects_changed_runtime_binary(tmp_path, monkeypatch):
    from roadeye import phase2

    monkeypatch.setattr(phase2, "ROOT", tmp_path)
    write_json(tmp_path / "window.json", {"scenario": "S02"})
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"frozen weights")
    config = {
        "window": "window.json",
        "run_role": "evaluation",
        "cityflow_training": False,
        "development_scenarios": ["S01"],
        "evaluation_scenarios": ["S02"],
        "selection_manifest": "selection.json",
    }
    config_path = tmp_path / "config.json"
    write_json(config_path, config)
    write_json(
        tmp_path / "selection.json",
        {
            "text_sha256": {
                "config.json": text_sha256(config_path),
                "window.json": text_sha256(tmp_path / "window.json"),
            },
            "binary_sha256": {"weights.pt": sha256(weights)},
        },
    )
    assert configuration(config_path)[1]["scenario"] == "S02"
    weights.write_bytes(b"changed weights")
    with pytest.raises(ValueError, match="Frozen binary changed"):
        configuration(config_path)
