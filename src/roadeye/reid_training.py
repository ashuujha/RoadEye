"""Portable, training-only vehicle Re-ID fine-tuning and artifact export."""

from __future__ import annotations

import json
import logging
import math
import platform
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterator

import numpy as np

from .tracklets import sha256, write_json
from .vehicle_encoder import VehicleEncoder, load_vehicle_encoder

LOGGER = logging.getLogger("roadeye.reid_training")
EXPORT_FORMAT = "roadeye_vehicle_encoder_v1"


def identity_split(
    identities_by_scenario: dict[str, list[str]], fraction: float, seed: int
) -> dict[str, str]:
    """Deterministic scenario-stratified, identity-disjoint split."""
    if not 0 < fraction < 0.5:
        raise ValueError("Development fraction must be between zero and one half")
    result: dict[str, str] = {}
    for offset, scenario in enumerate(sorted(identities_by_scenario)):
        identities = sorted(set(identities_by_scenario[scenario]))
        if len(identities) < 2:
            raise ValueError(f"Too few identities in {scenario}")
        random.Random(seed + offset).shuffle(identities)
        development_count = max(1, math.ceil(len(identities) * fraction))
        if development_count >= len(identities):
            raise ValueError(f"No training identities remain in {scenario}")
        development = set(identities[:development_count])
        result.update(
            {
                identity: "development" if identity in development else "train"
                for identity in identities
            }
        )
    if len(result) != sum(
        len(set(values)) for values in identities_by_scenario.values()
    ):
        raise ValueError("Scoped identities overlap across scenarios")
    return result


def batch_hard_triplet_loss(features, labels, margin: float):
    """Batch-hard triplet loss; every anchor must have a positive and negative."""
    import torch

    distances = torch.cdist(features, features)
    same = labels[:, None].eq(labels[None, :])
    same.fill_diagonal_(False)
    different = ~labels[:, None].eq(labels[None, :])
    if not same.any(dim=1).all() or not different.any(dim=1).all():
        raise ValueError("Every triplet anchor needs positive and negative examples")
    hardest_positive = distances.masked_fill(~same, float("-inf")).max(dim=1).values
    hardest_negative = distances.masked_fill(~different, float("inf")).min(dim=1).values
    return torch.relu(hardest_positive - hardest_negative + margin).mean()


def pooled_retrieval_metrics(
    features: np.ndarray, identities: list[str], cameras: list[str]
) -> dict:
    """Pool crops per identity/camera, then retrieve across different cameras."""
    if (
        not len(features)
        or len(features) != len(identities)
        or len(features) != len(cameras)
    ):
        raise ValueError("Invalid retrieval inputs")
    groups: dict[tuple[str, str], list[np.ndarray]] = defaultdict(list)
    for feature, identity, camera in zip(features, identities, cameras, strict=True):
        groups[(identity, camera)].append(feature)
    keys = sorted(groups)
    pooled = np.stack([np.mean(groups[key], axis=0) for key in keys]).astype(np.float32)
    pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
    rank1: list[bool] = []
    average_precisions: list[float] = []
    for index, (identity, camera) in enumerate(keys):
        gallery = [i for i, key in enumerate(keys) if key[1] != camera]
        positives = {i for i in gallery if keys[i][0] == identity}
        if not positives:
            continue
        ranked = sorted(
            gallery, key=lambda i: (-float(np.dot(pooled[index], pooled[i])), keys[i])
        )
        hits = np.array([i in positives for i in ranked])
        rank1.append(bool(hits[0]))
        precision = np.cumsum(hits) / np.arange(1, len(hits) + 1)
        average_precisions.append(float(np.sum(precision * hits) / len(positives)))
    return {
        "queries": len(rank1),
        "rank1_correct": sum(rank1),
        "rank1": sum(rank1) / len(rank1) if rank1 else None,
        "map": float(np.mean(average_precisions)) if average_precisions else None,
        "identity_camera_pools": len(keys),
        "scope": "identity_camera_pooled_cross_camera_development_retrieval",
    }


def evaluate_encoder(encoder, loader) -> dict:
    """Measure the frozen development protocol without changing model state."""
    import torch

    encoder.eval()
    vectors: list[np.ndarray] = []
    identities: list[str] = []
    cameras: list[str] = []
    with torch.inference_mode():
        for pixels, _, identity, camera in loader:
            features = torch.nn.functional.normalize(
                encoder(pixels.cuda(non_blocking=True)), dim=1
            )
            vectors.append(features.cpu().numpy())
            identities.extend(identity)
            cameras.extend(camera)
    if not vectors:
        raise ValueError("Development split produced no batches")
    return pooled_retrieval_metrics(np.concatenate(vectors), identities, cameras)


class CropDataset:
    def __init__(self, root: Path, records: list[dict], train: bool) -> None:
        from torchvision.transforms import (
            ColorJitter,
            Compose,
            InterpolationMode,
            PILToTensor,
            RandomCrop,
            RandomHorizontalFlip,
            Resize,
        )

        self.root, self.records = root, records
        self.identities = {
            identity: index
            for index, identity in enumerate(sorted({r["identity"] for r in records}))
        }
        transforms = [Resize((288, 288), interpolation=InterpolationMode.BICUBIC)]
        if train:
            transforms.extend(
                [
                    RandomCrop((256, 256)),
                    RandomHorizontalFlip(),
                    ColorJitter(0.2, 0.2, 0.1, 0.05),
                ]
            )
        else:
            transforms = [Resize((256, 256), interpolation=InterpolationMode.BICUBIC)]
        transforms.append(PILToTensor())
        self.transform = Compose(transforms)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        from PIL import Image

        record = self.records[index]
        with Image.open(self.root / record["image"]) as image:
            pixels = self.transform(image.convert("RGB")).float()
        return (
            pixels,
            self.identities[record["identity"]],
            record["identity"],
            record["camera"],
        )


class IdentityBatchSampler:
    def __init__(
        self, records: list[dict], identities_per_batch: int, instances: int, seed: int
    ) -> None:
        if identities_per_batch < 2 or instances < 2:
            raise ValueError(
                "Identity batches require at least two identities and two instances"
            )
        self.groups: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for index, record in enumerate(records):
            self.groups[record["identity"]][record["camera"]].append(index)
        if len(self.groups) < identities_per_batch:
            raise ValueError("Too few training identities for a batch")
        self.identities_per_batch = identities_per_batch
        self.instances = instances
        self.seed = seed
        self.epoch = 0

    def __len__(self) -> int:
        record_count = sum(
            len(indexes)
            for cameras in self.groups.values()
            for indexes in cameras.values()
        )
        return max(
            1,
            math.ceil(record_count / (self.identities_per_batch * self.instances)),
        )

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed + self.epoch)
        self.epoch += 1
        identities = sorted(self.groups)
        for _ in range(len(self)):
            selected = rng.sample(identities, self.identities_per_batch)
            batch = []
            for identity in selected:
                cameras = sorted(self.groups[identity])
                if len(cameras) < 2:
                    raise ValueError(f"Training identity lacks two cameras: {identity}")
                rng.shuffle(cameras)
                batch.extend(
                    rng.choice(self.groups[identity][cameras[index % len(cameras)]])
                    for index in range(self.instances)
                )
            yield batch


def load_records(bundle: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((bundle / "manifest.json").read_text())
    records_path = bundle / "records.jsonl"
    if sha256(records_path) != manifest["records_sha256"]:
        raise ValueError("Training records hash mismatch")
    records = [json.loads(line) for line in records_path.read_text().splitlines()]
    for record in records:
        image = bundle / record["image"]
        if not image.is_file() or sha256(image) != record["image_sha256"]:
            raise ValueError(f"Training image hash mismatch: {record['image']}")
    train_ids = {r["identity"] for r in records if r["split"] == "train"}
    development_ids = {r["identity"] for r in records if r["split"] == "development"}
    if train_ids & development_ids or not train_ids or not development_ids:
        raise ValueError("Training/development identity split is invalid")
    return manifest, records


def export_encoder(model: VehicleEncoder, path: Path, metadata: dict) -> dict:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    torch.save(
        {
            "format": EXPORT_FORMAT,
            "architecture": "fastreid_sbs_r50_ibn",
            "state_dict": state,
        },
        path,
    )
    result = {
        **metadata,
        "format": EXPORT_FORMAT,
        "weights_file": path.name,
        "weights_sha256": sha256(path),
    }
    write_json(path.with_suffix(".json"), result)
    return result


def train(bundle: Path, config_path: Path, initial_weights: Path, output: Path) -> dict:
    import torch
    import torchvision
    from torch import nn
    from torch.utils.data import DataLoader

    config = json.loads(config_path.read_text())
    policy = config["training"]
    if policy["device"] != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("This portable training job requires a CUDA GPU")
    if sha256(initial_weights) != config["initialization"]["sha256"]:
        raise ValueError("Initial checkpoint hash mismatch")
    manifest, records = load_records(bundle)
    if manifest["config_sha256"] != sha256(config_path):
        raise ValueError("Bundle was built with a different training configuration")
    torch.manual_seed(policy["seed"])
    torch.cuda.manual_seed_all(policy["seed"])
    np.random.seed(policy["seed"])
    random.seed(policy["seed"])
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    train_records = [r for r in records if r["split"] == "train"]
    development_records = [r for r in records if r["split"] == "development"]
    train_data = CropDataset(bundle, train_records, train=True)
    development_data = CropDataset(bundle, development_records, train=False)
    sampler = IdentityBatchSampler(
        train_records,
        policy["identities_per_batch"],
        policy["instances_per_identity"],
        policy["seed"],
    )
    loader_generator = torch.Generator().manual_seed(policy["seed"])
    train_loader = DataLoader(
        train_data,
        batch_sampler=sampler,
        num_workers=policy["num_workers"],
        pin_memory=True,
        generator=loader_generator,
    )
    development_loader = DataLoader(
        development_data,
        batch_size=64,
        shuffle=False,
        num_workers=policy["num_workers"],
        pin_memory=True,
        generator=loader_generator,
    )
    encoder = load_vehicle_encoder(initial_weights).requires_grad_(True).cuda()
    classifier = nn.Linear(2048, len(train_data.identities), bias=False).cuda()
    optimizer = torch.optim.AdamW(
        [*encoder.parameters(), *classifier.parameters()],
        lr=policy["learning_rate"],
        weight_decay=policy["weight_decay"],
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=policy["epochs"]
    )
    scaler = torch.amp.GradScaler("cuda")
    baseline_metrics = evaluate_encoder(encoder, development_loader)
    history = [{"epoch": 0, "development": baseline_metrics}]
    best = (
        (baseline_metrics["map"] or -1, baseline_metrics["rank1"] or -1, 0),
        0,
        {
            key: value.detach().cpu().clone()
            for key, value in encoder.state_dict().items()
        },
        baseline_metrics,
    )
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "history.json", history)
    started = time.perf_counter()
    for epoch in range(1, policy["epochs"] + 1):
        encoder.train(), classifier.train()
        totals = defaultdict(float)
        for pixels, labels, _, _ in train_loader:
            pixels, labels = (
                pixels.cuda(non_blocking=True),
                labels.cuda(non_blocking=True),
            )
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                features = torch.nn.functional.normalize(encoder(pixels), dim=1)
                cross_entropy = torch.nn.functional.cross_entropy(
                    classifier(features),
                    labels,
                    label_smoothing=policy["label_smoothing"],
                )
                triplet = batch_hard_triplet_loss(
                    features, labels, policy["triplet_margin"]
                )
                loss = (
                    policy["cross_entropy_weight"] * cross_entropy
                    + policy["triplet_weight"] * triplet
                )
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            totals["loss"] += float(loss.detach())
            totals["cross_entropy"] += float(cross_entropy.detach())
            totals["triplet"] += float(triplet.detach())
            totals["batches"] += 1
        scheduler.step()
        metrics = evaluate_encoder(encoder, development_loader)
        row = {
            "epoch": epoch,
            "learning_rate": scheduler.get_last_lr()[0],
            "loss": totals["loss"] / totals["batches"],
            "cross_entropy": totals["cross_entropy"] / totals["batches"],
            "triplet": totals["triplet"] / totals["batches"],
            "development": metrics,
        }
        history.append(row)
        write_json(output / "history.json", history)
        LOGGER.info(
            "epoch=%s loss=%.4f rank1=%s map=%s",
            epoch,
            row["loss"],
            metrics["rank1"],
            metrics["map"],
        )
        score = (metrics["map"] or -1, metrics["rank1"] or -1, -epoch)
        if score > best[0]:
            best = (
                score,
                epoch,
                {
                    key: value.detach().cpu().clone()
                    for key, value in encoder.state_dict().items()
                },
                metrics,
            )
    encoder.load_state_dict(best[2], strict=True)
    metadata = {
        "schema_version": 1,
        "architecture": "fastreid_sbs_r50_ibn",
        "training_scenarios": config["scenarios"],
        "evaluation_scenarios_used": [],
        "split_unit": config["split"]["unit"],
        "bundle_manifest_sha256": sha256(bundle / "manifest.json"),
        "training_config_sha256": sha256(config_path),
        "initial_weights_sha256": sha256(initial_weights),
        "best_epoch": best[1],
        "development_metrics": best[3],
        "baseline_development_metrics": baseline_metrics,
        "epochs_completed": len(history) - 1,
        "training_seconds": time.perf_counter() - started,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "cuda_device": torch.cuda.get_device_name(),
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "claims": config["claims"],
    }
    export = export_encoder(
        encoder.cpu(), output / config["export"]["filename"], metadata
    )
    write_json(output / config["export"]["manifest"], export)
    return export
