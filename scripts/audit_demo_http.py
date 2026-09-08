"""Exercise the live RoadEye demo routes and record observed HTTP latency."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from roadeye.tracklets import write_json


def request(base_url: str, path: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(base_url + path, timeout=30) as response:
            body = response.read()
            status = response.status
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as error:
        body = error.read()
        status = error.code
        content_type = error.headers.get_content_type()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "status": status,
        "content_type": content_type,
        "body": body,
        "elapsed_ms": elapsed_ms,
    }


def json_body(response: dict[str, Any]) -> Any:
    return json.loads(response["body"].decode("utf-8"))


def summary(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "samples": len(values),
        "mean_ms": statistics.fmean(values),
        "p50_ms": statistics.median(values),
        "p95_ms": ordered[p95_index],
        "max_ms": max(values),
    }


def measure(base_url: str, path: str, *, samples: int = 5) -> dict[str, Any]:
    warmup = request(base_url, path)
    if warmup["status"] != 200:
        raise RuntimeError(f"Warm-up failed for {path}: {warmup['status']}")
    responses = [request(base_url, path) for _ in range(samples)]
    if any(row["status"] != 200 for row in responses):
        raise RuntimeError(f"Measured request failed for {path}")
    return {
        **summary([row["elapsed_ms"] for row in responses]),
        "status": 200,
        "content_type": responses[0]["content_type"],
        "bytes": len(responses[0]["body"]),
    }


def audit(base_url: str, plate_query: str) -> dict[str, Any]:
    status = json_body(request(base_url, "/api/status"))
    vehicles = json_body(
        request(base_url, "/api/vehicles?multi_camera_only=true&limit=1")
    )
    if not vehicles:
        raise RuntimeError("Demo returned no multi-camera vehicle")
    global_id = vehicles[0]["global_id"]
    encoded_id = urllib.parse.quote(global_id, safe="")
    journey = json_body(request(base_url, f"/api/vehicles/{encoded_id}"))
    sample = journey["visits"][0]["evidence_samples"][0]
    crop_path = sample["crop_url"]
    frame_path = sample["source_frame_url"]
    plate_path = "/api/plate-search?" + urllib.parse.urlencode(
        {"q": plate_query, "limit": 25}
    )
    paths = {
        "status": "/api/status",
        "vehicles": "/api/vehicles?multi_camera_only=true&limit=50",
        "journey": f"/api/vehicles/{encoded_id}",
        "crop": crop_path,
        "frame": frame_path,
        "analytics": "/api/analytics",
        "plate_status": "/api/plate-search/status",
        "plate_search": plate_path,
    }
    timings = {name: measure(base_url, path) for name, path in paths.items()}

    frame_response = request(base_url, frame_path)
    decoded = cv2.imdecode(
        np.frombuffer(frame_response["body"], dtype=np.uint8), cv2.IMREAD_COLOR
    )
    if decoded is None:
        raise RuntimeError("Annotated source-frame response did not decode")
    plate_response = json_body(request(base_url, plate_path))
    if not plate_response["results"]:
        raise RuntimeError("Known runtime plate query returned no result")
    plate_result = plate_response["results"][0]
    linked_journey = json_body(request(base_url, plate_result["journey_url"]))
    linked_sample = linked_journey["visits"][plate_result["visit_index"]][
        "evidence_samples"
    ][plate_result["sample_index"]]
    if linked_sample["crop_sha256"] != plate_result["crop_sha256"]:
        raise RuntimeError("Plate result did not open its indexed evidence")

    errors = {
        "unknown_vehicle": request(base_url, "/api/vehicles/not-a-real-id")[
            "status"
        ],
        "unknown_sample": request(
            base_url,
            f"/api/vehicles/{encoded_id}/visits/999/samples/999/crop",
        )["status"],
        "short_plate_query": request(base_url, "/api/plate-search?q=A-1")[
            "status"
        ],
    }
    if errors != {
        "unknown_vehicle": 404,
        "unknown_sample": 404,
        "short_plate_query": 422,
    }:
        raise RuntimeError(f"Unexpected error-route behavior: {errors}")
    return {
        "status": "PASS",
        "scenario": status["scenario"],
        "runtime_status": status["status"],
        "disclosure": status.get("disclosure"),
        "plate_availability": status["plate_search"]["availability"],
        "plate_entry_count": status["plate_search"]["index_entry_count"],
        "timing_protocol": {
            "kind": "warm_local_http_observation_not_benchmark",
            "warmup_requests_per_route": 1,
            "measured_requests_per_route": 5,
        },
        "timings": timings,
        "frame_decode": {
            "status": "PASS",
            "height": int(decoded.shape[0]),
            "width": int(decoded.shape[1]),
        },
        "plate_handoff": {
            "status": "PASS",
            "global_id": plate_result["global_id"],
            "visit_index": plate_result["visit_index"],
            "sample_index": plate_result["sample_index"],
            "crop_sha256": plate_result["crop_sha256"],
            "prediction_status": plate_result["prediction_status"],
        },
        "error_routes": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--plate-query", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.base_url.rstrip("/"), args.plate_query)
    if args.output is not None:
        write_json(args.output, report)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
