"""RoadEye local command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .demo import ROOT, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Run the local test/demo interface")
    serve.add_argument("--config", type=Path, default=ROOT / "configs/demo.json")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "serve":
        uvicorn.run(create_app(args.config), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
