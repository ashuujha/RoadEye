"""CPU appearance descriptors; model downloading is an explicit preparation action."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .tracklets import sha256

WEIGHTS_URL = "https://download.pytorch.org/models/resnet50-11ad3fa6.pth"


def download_weights(path: Path, kind: str = "resnet50_imagenet1k_v2") -> None:
    import torch

    url, digest = WEIGHTS_URL, "11ad3fa6"
    if kind == "fastreid_veri_sbs_r50_ibn":
        from .vehicle_encoder import WEIGHTS_SHA256, WEIGHTS_URL as VEHICLE_URL

        url, digest = VEHICLE_URL, WEIGHTS_SHA256
    elif kind != "resnet50_imagenet1k_v2":
        raise ValueError("Unsupported appearance model")
    if path.exists():
        if not sha256(path).startswith(digest):
            raise ValueError(
                "Existing checkpoint does not match the official hash prefix"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.hub.download_url_to_file(url, str(path), hash_prefix=digest)


def embed(
    samples: dict, output: Path, config: dict, project: Path
) -> tuple[list[str], np.ndarray, dict]:
    import torch
    import torchvision
    from PIL import Image
    from torchvision.models import ResNet50_Weights, resnet50

    weights = project / config["weights"]
    if not weights.is_file():
        raise FileNotFoundError(
            "Missing weights; run the explicit fetch-weights command first"
        )
    digest = sha256(weights)
    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(0)
    vehicle = config["kind"] in {
        "fastreid_veri_sbs_r50_ibn",
        "roadeye_cityflow_reid_r50_ibn",
    }
    if vehicle:
        from torchvision.transforms import (
            Compose,
            InterpolationMode,
            PILToTensor,
            Resize,
        )

        from .vehicle_encoder import (
            WEIGHTS_URL as source_url,
            load_roadeye_encoder,
            load_vehicle_encoder,
        )

        if config["kind"] == "roadeye_cityflow_reid_r50_ibn":
            model = load_roadeye_encoder(weights, config["weights_sha256"])
            source_url = config["weights_source"]
        else:
            model = load_vehicle_encoder(weights)
        transform = Compose(
            [Resize((256, 256), interpolation=InterpolationMode.BICUBIC), PILToTensor()]
        )
    elif config["kind"] == "resnet50_imagenet1k_v2":
        if not digest.startswith("11ad3fa6"):
            raise ValueError("Checkpoint checksum mismatch")
        model = resnet50(weights=None)
        model.load_state_dict(
            torch.load(weights, map_location="cpu", weights_only=True)
        )
        model.fc = torch.nn.Identity()
        model.eval()
        transform = ResNet50_Weights.IMAGENET1K_V2.transforms()
        source_url = WEIGHTS_URL
    else:
        raise ValueError("Unsupported appearance model")
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
                model(torch.stack(tensors).float()), dim=1
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
        "trained_for_vehicle_reid": vehicle,
        "description": (
            "RoadEye-format FastReID SBS ResNet-50-IBN artifact; verify its adjacent training manifest before use"
            if config["kind"] == "roadeye_cityflow_reid_r50_ibn"
            else "FastReID SBS ResNet-50-IBN trained on VeRi; no RoadEye CityFlow training"
            if vehicle
            else "ImageNet ResNet-50 generic appearance fallback; no CityFlow training"
        ),
        "weights_sha256": digest,
        "weights_source": source_url,
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "device": "cpu",
        "dimensions": pooled.shape[1],
        "sampling": "first_K_quality_eligible_spaced_observations_within_bounded_prefix"
        if config.get("quality_prefix")
        else "first_K_observations_in_window; mean_of_normalized_prefix_features",
        "quality_prefix": config.get("quality_prefix"),
        "pooling": "mean_of_normalized_features_then_L2",
        "transforms": str(transform),
    }
    return keys, pooled, metadata
