"""Run the local demo while rejecting CityFlow ground-truth path access."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import uvicorn

from roadeye.demo import ROOT, create_app


@contextmanager
def reject_ground_truth_paths() -> Iterator[None]:
    original_open = Path.open

    def guarded_open(path: Path, *args, **kwargs):
        resolved = Path(path)
        parts = {part.casefold() for part in resolved.parts}
        if resolved.name.casefold() == "gt.txt" or "evaluation" in parts:
            raise RuntimeError(f"Runtime ground-truth access rejected: {resolved}")
        return original_open(resolved, *args, **kwargs)

    with patch.object(Path, "open", guarded_open):
        yield


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    config = (ROOT / args.config).resolve() if not args.config.is_absolute() else args.config
    with reject_ground_truth_paths():
        uvicorn.run(create_app(config), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
