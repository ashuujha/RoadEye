"""Explicitly fetch pinned Apache-2.0 references, then check CPU encoder parity.

This is an optional integration check; reference source is never imported by
RoadEye inference. It compares against the original backbone/pooling classes.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
from urllib.request import urlopen

import torch
import torch.nn.functional as functional
from torch import nn

from roadeye.phase2 import ROOT
from roadeye.tracklets import sha256, write_json
from roadeye.vehicle_encoder import load_vehicle_encoder

REVISION = "c9bc3ceb2f7a6438b62fb515ea3df6d1e999e95d"
SOURCES = {
    "fastreid/layers/batch_norm.py": {"IBN"},
    "fastreid/layers/non_local.py": {"Non_local"},
    "fastreid/layers/pooling.py": {"GeneralizedMeanPooling", "GeneralizedMeanPoolingP"},
    "fastreid/modeling/backbones/resnet.py": {"BasicBlock", "Bottleneck", "ResNet"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-reference", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "artifacts/reference/fastreid-pinned"
    directory.mkdir(parents=True, exist_ok=True)
    namespace = {
        "torch": torch,
        "nn": nn,
        "F": functional,
        "math": math,
        "get_norm": lambda name, channels, **kwargs: nn.BatchNorm2d(channels),
    }
    hashes = {}
    for relative, names in SOURCES.items():
        path = directory / relative.replace("/", "__")
        if args.fetch_reference:
            url = f"https://raw.githubusercontent.com/JDAI-CV/fast-reid/{REVISION}/{relative}"
            with urlopen(url, timeout=30) as response:
                path.write_bytes(response.read())
        hashes[relative] = sha256(path)
        tree = ast.parse(path.read_text())
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name in names
        ]
        if {node.name for node in classes} != names:
            raise ValueError("Missing upstream reference classes")
        exec(
            compile(ast.Module(body=classes, type_ignores=[]), str(path), "exec"),
            namespace,
        )
    torch.set_num_threads(4)
    torch.manual_seed(0)
    path = ROOT / "artifacts/models/veri_sbs_R50-ibn.pth"
    adapter = load_vehicle_encoder(path)
    state = torch.load(path, map_location="cpu", weights_only=True)["model"]
    reference = namespace["ResNet"](
        1, "BN", True, False, True, namespace["Bottleneck"], [3, 4, 6, 3], [0, 2, 3, 0]
    ).eval()
    reference.load_state_dict(
        {
            k.removeprefix("backbone."): v
            for k, v in state.items()
            if k.startswith("backbone.")
        },
        strict=True,
    )
    pool = namespace["GeneralizedMeanPoolingP"]()
    pool.load_state_dict({"p": state["heads.pool_layer.p"]})
    pixels = torch.rand(2, 3, 256, 256) * 255
    with torch.inference_mode():
        actual = adapter(pixels)
        expected = pool(reference((pixels - state["pixel_mean"]) / state["pixel_std"]))
        expected = functional.batch_norm(
            expected,
            state["heads.bottleneck.0.running_mean"],
            state["heads.bottleneck.0.running_var"],
            state["heads.bottleneck.0.weight"],
            state["heads.bottleneck.0.bias"],
            training=False,
        ).flatten(1)
    torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-5)
    report = {
        "status": "PASS",
        "device": "cpu",
        "input_shape": list(pixels.shape),
        "reference_revision": REVISION,
        "reference_sha256": hashes,
        "checkpoint_sha256": sha256(path),
        "adapter_sha256": sha256(ROOT / "src/roadeye/vehicle_encoder.py"),
        "max_absolute_error": float((actual - expected).abs().max()),
        "scope": "raw descriptor parity against upstream backbone, IBN, non-local and GeM operations; synthetic input, not accuracy",
    }
    write_json(ROOT / "reports/reid-encoder-parity.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
