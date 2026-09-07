"""Training protocol tests use synthetic labels and tensors, never demo assets."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image
from torch import nn

from roadeye.embeddings import embed
from roadeye.reid_training import (
    IdentityBatchSampler,
    batch_hard_triplet_loss,
    identity_split,
    pooled_retrieval_metrics,
    train,
)
from roadeye.tracklets import sha256


def test_identity_split_is_deterministic_stratified_and_disjoint():
    identities = {
        "S01": [f"train/S01/{index}" for index in range(10)],
        "S03": [f"train/S03/{index}" for index in range(5)],
    }
    first = identity_split(identities, 0.2, 42)
    second = identity_split(identities, 0.2, 42)
    assert first == second
    assert Counter((key.split("/")[1], value) for key, value in first.items()) == {
        ("S01", "train"): 8,
        ("S01", "development"): 2,
        ("S03", "train"): 4,
        ("S03", "development"): 1,
    }
    assert set(first) == {
        identity for scenario in identities.values() for identity in scenario
    }


def test_identity_batch_contains_cross_camera_positives():
    records = [
        {"identity": identity, "camera": camera}
        for identity in ("a", "b", "c")
        for camera in ("c1", "c2")
        for _ in range(2)
    ]
    sampler = IdentityBatchSampler(records, identities_per_batch=2, instances=4, seed=7)
    batch = next(iter(sampler))
    selected = [records[index] for index in batch]
    assert len(batch) == 8
    for identity in {row["identity"] for row in selected}:
        assert {row["camera"] for row in selected if row["identity"] == identity} == {
            "c1",
            "c2",
        }


def test_batch_hard_triplet_rewards_separated_identities():
    labels = torch.tensor([0, 0, 1, 1])
    separated = torch.tensor([[1.0, 0], [0.9, 0.1], [-1.0, 0], [-0.9, -0.1]])
    collapsed = torch.tensor([[1.0, 0], [-1.0, 0], [0.9, 0.1], [-0.9, -0.1]])
    assert batch_hard_triplet_loss(separated, labels, 0.3) < batch_hard_triplet_loss(
        collapsed, labels, 0.3
    )


def test_pooled_retrieval_reports_exact_cross_camera_result():
    features = np.array([[1, 0], [1, 0], [0, 1], [0, 1]], dtype=np.float32)
    result = pooled_retrieval_metrics(
        features, ["a", "a", "b", "b"], ["c1", "c2", "c1", "c2"]
    )
    assert result["queries"] == 4
    assert result["rank1"] == 1.0
    assert result["map"] == 1.0


def test_export_loader_requires_hash_format_and_strict_state(tmp_path, monkeypatch):
    import roadeye.vehicle_encoder as module

    class TinyEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.linear = nn.Linear(2, 2)
            self.register_buffer("pixel_std", torch.ones(1))

    monkeypatch.setattr(module, "VehicleEncoder", TinyEncoder)
    model = TinyEncoder()
    path = tmp_path / "encoder.pt"
    torch.save(
        {
            "format": "roadeye_vehicle_encoder_v1",
            "architecture": "fastreid_sbs_r50_ibn",
            "state_dict": model.state_dict(),
        },
        path,
    )
    loaded = module.load_roadeye_encoder(path, sha256(path))
    assert not loaded.training
    assert all(not parameter.requires_grad for parameter in loaded.parameters())
    with pytest.raises(ValueError, match="checksum"):
        module.load_roadeye_encoder(path, "0" * 64)
    payload = torch.load(path, weights_only=True)
    payload["invented"] = True
    torch.save(payload, path)
    with pytest.raises(ValueError, match="payload"):
        module.load_roadeye_encoder(path, sha256(path))


def test_training_configuration_excludes_consumed_evaluation_scenarios():
    config = json.loads(Path("configs/reid-training.json").read_text(encoding="utf-8"))
    assert config["scenarios"] == ["S01", "S03"]
    assert set(config["scenarios"]).isdisjoint(config["allowed_evaluation_scenarios"])
    assert set(config["allowed_evaluation_scenarios"]) == {"S02", "S04", "S05"}
    assert config["split"]["unit"] == "scoped_identity"


def test_training_refuses_cpu_execution_before_reading_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"training": {"device": "cuda"}}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="requires a CUDA GPU"):
        train(tmp_path / "missing", config, tmp_path / "missing.pt", tmp_path / "out")


def test_embedding_pipeline_accepts_exact_hash_roadeye_export(tmp_path, monkeypatch):
    import roadeye.vehicle_encoder as encoder_module

    class TinyEncoder(nn.Module):
        def forward(self, pixels):
            return pixels.mean(dim=(2, 3))

    project = tmp_path / "project"
    output = tmp_path / "crops"
    project.mkdir()
    output.mkdir()
    weights = project / "encoder.pt"
    weights.write_bytes(b"test encoder payload")
    Image.new("RGB", (32, 24), (10, 20, 30)).save(output / "crop.jpg")
    expected_hash = sha256(weights)

    def fake_loader(path, supplied_hash):
        assert path == weights
        assert supplied_hash == expected_hash
        return TinyEncoder().eval()

    monkeypatch.setattr(encoder_module, "load_roadeye_encoder", fake_loader)
    keys, vectors, metadata = embed(
        {"track": [{"crop": "crop.jpg"}]},
        output,
        {
            "kind": "roadeye_cityflow_reid_r50_ibn",
            "weights": "encoder.pt",
            "weights_sha256": expected_hash,
            "weights_source": "private_training_export",
            "cpu_threads": 1,
            "batch_size": 1,
        },
        project,
    )
    assert keys == ["track"]
    assert vectors.shape == (1, 3)
    assert np.isclose(np.linalg.norm(vectors[0]), 1.0)
    assert metadata["weights_sha256"] == expected_hash
    assert metadata["device"] == "cpu"
