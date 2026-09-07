"""Run the RoadEye training-only Re-ID job on a CUDA machine/Colab."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from roadeye.reid_training import train


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--initial-weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    print(
        json.dumps(
            train(args.bundle, args.config, args.initial_weights, args.output),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
