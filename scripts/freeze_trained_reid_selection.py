"""Freeze the accepted trained model and S02 runtime inputs before GT scoring."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from roadeye.phase2 import ROOT
from roadeye.tracklets import sha256, text_sha256, write_json

CONFIG = ROOT / "configs/reid-trained-evaluation.json"
OUTPUT = ROOT / "reports/reid-trained-selection.json"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("Trained-model selection is already frozen")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    weights = ROOT / config["embedding"]["weights"]
    sources = [
        CONFIG,
        ROOT / "configs/reid-trained-experiment.json",
        ROOT / config["window"],
        ROOT / config["training_provenance"],
        *sorted((ROOT / "src/roadeye").glob("*.py")),
    ]
    freeze = {
        "schema_version": 1,
        "selected_at_utc": datetime.now(timezone.utc).isoformat(),
        "text_hash_rule": "SHA256 of UTF-8 file bytes with CRLF normalized to LF",
        "text_sha256": {
            path.relative_to(ROOT).as_posix(): text_sha256(path) for path in sources
        },
        "binary_sha256": {
            weights.relative_to(ROOT).as_posix(): sha256(weights),
        },
        "selected_model": config["embedding"]["kind"],
        "selected_weights_sha256": config["embedding"]["weights_sha256"],
        "association_policy": config["association"],
        "evaluation_scenario": "S02",
        "evaluation_labels_opened_at_freeze": False,
        "scope": "returned model acceptance and unchanged association policy only; S02 metrics do not exist yet",
    }
    if freeze["selected_weights_sha256"] != sha256(weights):
        raise ValueError("Selected model hash mismatch")
    write_json(OUTPUT, freeze)
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
