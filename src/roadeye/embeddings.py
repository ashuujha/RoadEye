"""CPU appearance descriptors; model downloading is an explicit preparation action."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .tracklets import sha256

WEIGHTS_URL = "https://download.pytorch.org/models/resnet50-11ad3fa6.pth"


def download_weights(path: Path) -> None:
    import torch

    if path.exists():
        if not sha256(path).startswith("11ad3fa6"):
            raise ValueError(
                "Existing checkpoint does not match the official hash prefix"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.hub.download_url_to_file(WEIGHTS_URL, str(path), hash_prefix="11ad3fa6")


def embed(
    samples: dict, output: Path, config: dict, project: Path
) -> tuple[list[str], np.ndarray, dict]:
    import torch
    import torchvision
    from PIL import Image
    from torchvision.models import ResNet50_Weights, resnet50

    if config["kind"] != "resnet50_imagenet1k_v2":
        raise ValueError("Unsupported appearance model")
    weights = project / config["weights"]
    if not weights.is_file():
        raise FileNotFoundError(
            "Missing weights; run the explicit fetch-weights command first"
        )
    digest = sha256(weights)
    if not digest.startswith("11ad3fa6"):
        raise ValueError("Checkpoint checksum mismatch")
    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(0)
    model = resnet50(weights=None)
    model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))
    model.fc = torch.nn.Identity()
    model.eval()
    transform = ResNet50_Weights.IMAGENET1K_V2.transforms()
    keys = sorted(samples)
    tasks = [(key, sample) for key in keys for sample in samples[key]]
    vectors: dict[str, list[np.ndarray]] = {key: [] for key in keys}
    batch_size = config["batch_size"]
    with torch.inference_mode():
        for start in range(0, len(tasks), batch_size):
            batch = tasks[start : start + batch_size]
            tensors = []
            for _, sample in batch:
                with Image.open(output / sample["crop"]) as image:
                    tensors.append(transform(image.convert("RGB")))
            features = torch.nn.functional.normalize(
                model(torch.stack(tensors)), dim=1
            ).numpy()
            for (key, _), feature in zip(batch, features, strict=True):
                vectors[key].append(feature)
            if start % (batch_size * 10) == 0:
                print(
                    f"CPU embeddings: {min(start+batch_size, len(tasks))}/{len(tasks)} crops",
                    flush=True,
                )
    if not keys:
        raise ValueError("No valid tracklet crop prefixes")
    pooled = np.stack([np.mean(vectors[key], axis=0) for key in keys]).astype(
        np.float32
    )
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    if not np.isfinite(pooled).all() or np.any(norms == 0):
        raise ValueError("Invalid embeddings")
    pooled /= norms
    metadata = {
        "model": config["kind"],
        "trained_for_vehicle_reid": False,
        "description": "ImageNet ResNet-50 generic appearance fallback; no CityFlow training",
        "weights_sha256": digest,
        "weights_source": WEIGHTS_URL,
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "device": "cpu",
        "dimensions": pooled.shape[1],
        "sampling": "first_K_observations_in_window; mean_of_normalized_prefix_features",
        "transforms": str(transform),
    }
    return keys, pooled, metadata
