"""Prediction-only aggregate analytics with explicit claim boundaries."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Mapping, Sequence


def _finite_time(value: object, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite journey time: {label}")
    return result


def _share(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _sorted_counts(
    counts: Mapping[tuple[str, str], int],
) -> list[tuple[tuple[str, str], int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], *item[0]))


def build_prediction_analytics(
    *,
    journeys: Sequence[Mapping[str, Any]],
    camera_positions: Mapping[str, Mapping[str, Any]],
    predicted_link_count: int,
    scenario: str,
    disclosure: str | None,
    source_prediction_sha256: str,
) -> dict[str, Any]:
    """Aggregate runtime predictions without loading identities or evaluator data."""

    visit_counts: dict[str, int] = defaultdict(int)
    vehicle_ids_by_camera: dict[str, set[str]] = defaultdict(set)
    multi_ids_by_camera: dict[str, set[str]] = defaultdict(set)
    od_counts: dict[tuple[str, str], int] = defaultdict(int)
    transition_gaps: dict[tuple[str, str], list[float]] = defaultdict(list)
    all_first_times: list[float] = []
    all_last_times: list[float] = []
    seen_ids: set[str] = set()
    multi_camera_count = 0
    observed_visit_count = 0
    calculated_transition_count = 0

    for journey in journeys:
        global_id = str(journey["global_id"])
        if global_id in seen_ids:
            raise ValueError(f"Duplicate global vehicle ID in analytics: {global_id}")
        seen_ids.add(global_id)
        visits = list(journey.get("visits", []))
        if not visits:
            raise ValueError(f"Journey has no observed visits: {global_id}")
        cameras = {str(visit["camera"]) for visit in visits}
        if int(journey["camera_count"]) != len(cameras):
            raise ValueError(f"Journey camera count mismatch: {global_id}")
        is_multi_camera = len(cameras) > 1
        if is_multi_camera:
            multi_camera_count += 1

        previous_camera: str | None = None
        previous_first: float | None = None
        previous_last: float | None = None
        for visit in visits:
            camera = str(visit["camera"])
            first = _finite_time(visit["first_observed_s"], global_id)
            last = _finite_time(visit["last_observed_s"], global_id)
            if first > last:
                raise ValueError(f"Journey visit has reversed times: {global_id}")
            if previous_first is not None and first < previous_first:
                raise ValueError(f"Journey visits are not chronological: {global_id}")
            if camera not in camera_positions:
                raise ValueError(f"Journey camera has no reference position: {camera}")
            visit_counts[camera] += 1
            vehicle_ids_by_camera[camera].add(global_id)
            if is_multi_camera:
                multi_ids_by_camera[camera].add(global_id)
            observed_visit_count += 1
            all_first_times.append(first)
            all_last_times.append(last)
            if previous_camera is not None and previous_last is not None:
                transition_gaps[(previous_camera, camera)].append(first - previous_last)
                calculated_transition_count += 1
            previous_camera = camera
            previous_first = first
            previous_last = last

        if is_multi_camera:
            origin = str(visits[0]["camera"])
            destination = str(visits[-1]["camera"])
            od_counts[(origin, destination)] += 1

    if calculated_transition_count != predicted_link_count:
        raise ValueError(
            "Predicted link count differs from journey transitions: "
            f"{predicted_link_count} != {calculated_transition_count}"
        )

    density = []
    for camera in camera_positions:
        count = visit_counts[camera]
        density.append(
            {
                "camera": camera,
                "observed_runtime_visit_count": count,
                "predicted_unique_vehicle_count": len(vehicle_ids_by_camera[camera]),
                "multi_camera_predicted_vehicle_count": len(
                    multi_ids_by_camera[camera]
                ),
                "share_of_observed_runtime_visits": _share(
                    count, observed_visit_count
                ),
                "position": dict(camera_positions[camera]),
                "measurement_status": (
                    "runtime_prediction_visit_count_not_traffic_density"
                ),
            }
        )
    density.sort(
        key=lambda row: (-row["observed_runtime_visit_count"], row["camera"])
    )

    od_pairs = [
        {
            "origin_camera": origin,
            "destination_camera": destination,
            "predicted_vehicle_count": count,
            "share_of_multi_camera_predictions": _share(count, multi_camera_count),
            "measurement_status": "predicted_endpoints_not_verified_od_flow",
        }
        for (origin, destination), count in _sorted_counts(od_counts)
    ]

    bottleneck_proxies = []
    transition_counts = {pair: len(gaps) for pair, gaps in transition_gaps.items()}
    for rank, ((source, target), count) in enumerate(
        _sorted_counts(transition_counts), 1
    ):
        gaps = transition_gaps[(source, target)]
        bottleneck_proxies.append(
            {
                "rank": rank,
                "from_camera": source,
                "to_camera": target,
                "predicted_transition_count": count,
                "share_of_predicted_transitions": _share(
                    count, calculated_transition_count
                ),
                "median_observed_boundary_gap_s": round(statistics.median(gaps), 6),
                "maximum_observed_boundary_gap_s": round(max(gaps), 6),
                "measurement_status": (
                    "predicted_transition_support_not_congestion_or_route_time"
                ),
            }
        )

    return {
        "schema_version": 1,
        "status": "UNVERIFIED",
        "scope": "prediction_only_aggregate_runtime_analytics",
        "scenario": scenario,
        "disclosure": disclosure,
        "source_prediction_sha256": source_prediction_sha256,
        "summary": {
            "predicted_global_vehicle_ids": len(journeys),
            "multi_camera_predicted_vehicle_ids": multi_camera_count,
            "observed_runtime_visits": observed_visit_count,
            "predicted_transitions": calculated_transition_count,
            "camera_count": len(camera_positions),
            "first_observed_s": min(all_first_times) if all_first_times else None,
            "last_observed_s": max(all_last_times) if all_last_times else None,
        },
        "camera_density": density,
        "origin_destination_pairs": od_pairs,
        "bottleneck_proxies": bottleneck_proxies,
        "claim_boundaries": {
            "uses_runtime_ground_truth": False,
            "counts_model_predicted_identities": True,
            "camera_density_is_traffic_volume": False,
            "origin_destination_is_verified_flow": False,
            "bottleneck_proxy_is_congestion": False,
            "boundary_gap_is_route_travel_time": False,
            "plate_or_owner_data_used": False,
        },
    }
