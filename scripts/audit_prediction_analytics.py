"""Rehearse and record aggregate analytics over a frozen demo runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from roadeye.demo import DemoRepository, create_app  # noqa: E402
from roadeye.tracklets import write_json  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "demo-s06.json"
DEFAULT_OUTPUT = ROOT / "reports" / "prediction-analytics-s06.json"


def resolve_from_root(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def audit(config_path: Path) -> dict:
    """Load verified runtime artifacts and return identity-free aggregates."""

    repository = DemoRepository(config_path)
    analytics = repository.analytics()
    api_routes = {
        route.path for route in create_app(config_path).routes if route.path.startswith("/api/")
    }
    if "/api/analytics" not in api_routes:
        raise ValueError("Analytics API route is missing")
    if analytics["status"] != "UNVERIFIED":
        raise ValueError("Prediction analytics must remain UNVERIFIED")
    if analytics["claim_boundaries"]["uses_runtime_ground_truth"]:
        raise ValueError("Prediction analytics cannot use runtime ground truth")
    encoded = json.dumps(analytics, sort_keys=True)
    if "roadeye_" in encoded or "plate_text" in encoded:
        raise ValueError("Aggregate audit contains a prohibited identity field")
    return {
        **analytics,
        "verification": {
            "runtime_artifact_integrity": repository.status()[
                "runtime_artifact_integrity"
            ],
            "analytics_route": "/api/analytics",
            "analytics_route_present": True,
            "contains_global_vehicle_ids": False,
            "contains_plate_strings": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = resolve_from_root(args.output)
    report = audit(resolve_from_root(args.config))
    write_json(output, report)
    print(f"PASS: wrote {output.relative_to(ROOT)}")
    summary = report["summary"]
    print(
        "predicted IDs={predicted_global_vehicle_ids}; "
        "multi-camera={multi_camera_predicted_vehicle_ids}; "
        "visits={observed_runtime_visits}; links={predicted_transitions}".format(
            **summary
        )
    )


if __name__ == "__main__":
    main()
