"""CPU inference adapter for the official FastReID VeRi SBS R50-IBN checkpoint.

Adapted from Apache-2.0 FastReID components by JDAI/liaoxingyu. See
third_party/fastreid/NOTICE.md and LICENSE. No training or downloads here.
"""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn
from torchvision.models import resnet50

WEIGHTS_URL = (
    "https://github.com/JDAI-CV/fast-reid/releases/download/v0.1.1/veri_sbs_R50-ibn.pth"
)
WEIGHTS_SHA256 = "57fb9c17d88911ea64390bf5427f43511435e7f88f6eed9dbc969d4b611e53cd"


class InstanceBatchNorm(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.IN = nn.InstanceNorm2d(channels // 2, affine=True)
        self.BN = nn.BatchNorm2d(channels - channels // 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        left, right = x.chunk(2, dim=1)
        return torch.cat(
            (self.IN(left.contiguous()), self.BN(right.contiguous())), dim=1
        )


class NonLocal(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        # This release uses ONE intermediate channel (verified in source and weights).
        self.g = nn.Conv2d(channels, 1, 1)
        self.theta = nn.Conv2d(channels, 1, 1)
        self.phi = nn.Conv2d(channels, 1, 1)
        self.W = nn.Sequential(nn.Conv2d(1, channels, 1), nn.BatchNorm2d(channels))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        g = self.g(x).flatten(2).transpose(1, 2)
        theta = self.theta(x).flatten(2).transpose(1, 2)
        phi = self.phi(x).flatten(2)
        attention = torch.matmul(theta, phi) / phi.shape[-1]
        y = torch.matmul(attention, g).transpose(1, 2).contiguous()
        return x + self.W(y.reshape(x.shape[0], 1, x.shape[2], x.shape[3]))


class GeneralizedMeanPool(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.p = nn.Parameter(torch.ones(1) * 3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return nn.functional.adaptive_avg_pool2d(x.clamp(min=1e-6).pow(self.p), 1).pow(
            1 / self.p
        )


class VehicleEncoder(nn.Module):
    """2048-D post-BN descriptor, RGB float pixels in [0,255], 256x256 input."""

    def __init__(self) -> None:
        super().__init__()
        self.backbone = resnet50(weights=None)
        self.backbone.fc = nn.Identity()
        self.backbone.maxpool = nn.MaxPool2d(3, stride=2, ceil_mode=True)
        # FastReID's last spatial stride is 1, and IBN occurs in stages 1-3.
        self.backbone.layer4[0].conv2.stride = (1, 1)
        self.backbone.layer4[0].downsample[0].stride = (1, 1)
        for stage in (self.backbone.layer1, self.backbone.layer2, self.backbone.layer3):
            for block in stage:
                block.bn1 = InstanceBatchNorm(block.conv1.out_channels)
        self.backbone.NL_2 = nn.ModuleList([NonLocal(512) for _ in range(2)])
        self.backbone.NL_3 = nn.ModuleList([NonLocal(1024) for _ in range(3)])
        self.heads = nn.Module()
        self.heads.pool_layer = GeneralizedMeanPool()
        self.heads.bottleneck = nn.Sequential(nn.BatchNorm2d(2048))
        self.register_buffer("pixel_mean", torch.zeros(1, 3, 1, 1))
        self.register_buffer("pixel_std", torch.ones(1, 3, 1, 1))

    def forward(self, pixels: torch.Tensor) -> torch.Tensor:
        x = (pixels - self.pixel_mean) / self.pixel_std
        backbone = self.backbone
        x = backbone.maxpool(backbone.relu(backbone.bn1(backbone.conv1(x))))
        x = backbone.layer1(x)
        for index, block in enumerate(backbone.layer2):
            x = block(x)
            if index >= 2:
                x = backbone.NL_2[index - 2](x)
        for index, block in enumerate(backbone.layer3):
            x = block(x)
            if index >= 3:
                x = backbone.NL_3[index - 3](x)
        x = backbone.layer4(x)
        return self.heads.bottleneck(self.heads.pool_layer(x)).flatten(1)


def load_vehicle_encoder(path: Path) -> VehicleEncoder:
    from .tracklets import sha256

    if sha256(path) != WEIGHTS_SHA256:
        raise ValueError("Vehicle checkpoint checksum mismatch")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    state = dict(checkpoint["model"])
    # Legacy release carries a training-only classifier and an old BN counter name.
    classifier = state.pop("heads.classifier.weight")
    if tuple(classifier.shape) != (575, 2048):
        raise ValueError("Unexpected VeRi training classifier")
    state["heads.bottleneck.0.num_batches_tracked"] = state.pop(
        "heads.bnneck.num_batches_tracked"
    )
    model = VehicleEncoder()
    model.load_state_dict(state, strict=True)
    if not torch.all(model.pixel_std > 0):
        raise ValueError("Invalid checkpoint normalization")
    return model.eval().requires_grad_(False)


def load_roadeye_encoder(path: Path, expected_sha256: str) -> VehicleEncoder:
    """Load a training-job export with an externally recorded exact checksum."""
    from .tracklets import sha256

    if len(expected_sha256) != 64 or sha256(path) != expected_sha256:
        raise ValueError("RoadEye encoder checksum mismatch")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if set(checkpoint) != {"format", "architecture", "state_dict"}:
        raise ValueError("Unexpected RoadEye encoder payload")
    if (
        checkpoint["format"] != "roadeye_vehicle_encoder_v1"
        or checkpoint["architecture"] != "fastreid_sbs_r50_ibn"
    ):
        raise ValueError("Unsupported RoadEye encoder format")
    model = VehicleEncoder()
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    if not torch.all(model.pixel_std > 0):
        raise ValueError("Invalid RoadEye checkpoint normalization")
    return model.eval().requires_grad_(False)
