"""Tests for prediction-only aggregate analytics and claim boundaries."""

from __future__ import annotations

import pytest

from roadeye.analytics import build_prediction_analytics


POSITIONS = {
    "c1": {"latitude": 1.0, "longitude": 2.0, "kind": "approximate"},
    "c2": {"latitude": 1.1, "longitude": 2.1, "kind": "approximate"},
    "c3": {"latitude": 1.2, "longitude": 2.2, "kind": "approximate"},
}


def _visit(camera: str, first: float, last: float) -> dict:
    return {
        "camera": camera,
        "first_observed_s": first,
        "last_observed_s": last,
    }


def _journeys() -> list[dict]:
    return [
        {
            "global_id": "roadeye_a",
            "camera_count": 3,
            "visits": [
                _visit("c1", 0.0, 1.0),
                _visit("c2", 3.0, 4.0),
                _visit("c3", 8.0, 9.0),
            ],
        },
        {
            "global_id": "roadeye_b",
            "camera_count": 2,
            "visits": [_visit("c1", 10.0, 11.0), _visit("c2", 13.0, 14.0)],
        },
        {
            "global_id": "roadeye_c",
            "camera_count": 1,
            "visits": [_visit("c3", 20.0, 21.0)],
        },
    ]


def _analytics(**overrides) -> dict:
    arguments = {
        "journeys": _journeys(),
        "camera_positions": POSITIONS,
        "predicted_link_count": 3,
        "scenario": "fixture",
        "disclosure": "unverified fixture",
        "source_prediction_sha256": "abc123",
    }
    arguments.update(overrides)
    return build_prediction_analytics(**arguments)


def test_prediction_analytics_counts_visits_od_and_transitions() -> None:
    report = _analytics()

    assert report["summary"] == {
        "predicted_global_vehicle_ids": 3,
        "multi_camera_predicted_vehicle_ids": 2,
        "observed_runtime_visits": 6,
        "predicted_transitions": 3,
        "camera_count": 3,
        "first_observed_s": 0.0,
        "last_observed_s": 21.0,
    }
    assert report["camera_density"][0]["camera"] == "c1"
    assert report["camera_density"][0]["observed_runtime_visit_count"] == 2
    assert report["origin_destination_pairs"][0]["origin_camera"] == "c1"
    assert report["origin_destination_pairs"][0]["destination_camera"] == "c2"
    assert report["bottleneck_proxies"][0]["predicted_transition_count"] == 2
    assert report["bottleneck_proxies"][0]["median_observed_boundary_gap_s"] == 2.0


def test_prediction_analytics_never_promotes_aggregate_claims() -> None:
    report = _analytics()

    assert report["status"] == "UNVERIFIED"
    assert report["claim_boundaries"] == {
        "uses_runtime_ground_truth": False,
        "counts_model_predicted_identities": True,
        "camera_density_is_traffic_volume": False,
        "origin_destination_is_verified_flow": False,
        "bottleneck_proxy_is_congestion": False,
        "boundary_gap_is_route_travel_time": False,
        "plate_or_owner_data_used": False,
    }


def test_prediction_analytics_rejects_link_count_mismatch() -> None:
    with pytest.raises(ValueError, match="Predicted link count differs"):
        _analytics(predicted_link_count=4)


def test_prediction_analytics_preserves_overlapping_camera_boundaries() -> None:
    journeys = _journeys()
    journeys[0]["visits"][1]["first_observed_s"] = 0.5
    report = _analytics(journeys=journeys)

    assert report["bottleneck_proxies"][0]["median_observed_boundary_gap_s"] == 0.75


def test_prediction_analytics_rejects_out_of_order_visits() -> None:
    journeys = _journeys()
    journeys[0]["visits"][1]["first_observed_s"] = -0.5
    with pytest.raises(ValueError, match="not chronological"):
        _analytics(journeys=journeys)
