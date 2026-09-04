from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from roadeye.analytics import percentile
from roadeye.contracts import Reading, Window
from roadeye.plates import consensus, normalize
from roadeye.trajectories import paths, reconstruct


@pytest.mark.parametrize(
    "raw,expected",
    [
        (" zz-01 aa 0001 ", ["ZZ01AA0001"]),
        ("ZZO1AA000I", ["ZZ01AA0001"]),
        ("ZZ01AA001", []),
        ("ABC1234", []),
        ("ZZ01AA0?01", []),
        ("zz01a00001", ["ZZ01AO0001"]),
        ("ZZ01OO0001", ["ZZ01OO0001"]),
        ("ＺＺ01AA0001", []),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_consensus_boundary_duplicate_and_unsupported():
    reading = Reading.model_validate(
        {"frame_id": "f", "candidates": [{"text": "ZZ01AA0001", "confidence": 0.8}]}
    )
    assert consensus([reading], 1, 1)["status"] == "accepted"
    assert consensus([reading] * 10, 1, 1)["score"] == 0.8
    assert consensus([reading], 1, 0.999)["status"] == "review_required"
    assert consensus([], 1, 1)["reasons"] == ["NO_SUPPORTED_CANDIDATE"]
    other = Reading.model_validate(
        {"frame_id": "g", "candidates": [{"text": "ZZ01AA0002", "confidence": 0.8}]}
    )
    assert consensus([reading, other], 1, 1)["status"] == "review_required"


def node(id, camera, seconds):
    return {
        "id": id,
        "camera_id": camera,
        "captured_at": datetime.fromtimestamp(seconds, timezone.utc).isoformat(),
        "plate": "ZZ01AA0001",
        "status": "accepted",
        "score": 0.95,
    }


EDGES = [
    {
        "source": a,
        "target": b,
        "distance_m": 1000,
        "min_seconds": 30,
        "max_seconds": 300,
        "baseline_seconds": 60,
    }
    for a, b in [("C1", "C2"), ("C2", "C3"), ("C2", "C4")]
]


def test_directed_impossible_collision_and_branch():
    assert paths(EDGES, "C3", "C1") == []
    result = reconstruct([node("a", "C1", 0), node("b", "C3", 5)], EDGES, "ZZ01AA0001")
    assert result["rejected_links"][0]["reason"] == "IMPOSSIBLE_TRAVEL"
    result = reconstruct([node("a", "C1", 0), node("b", "C3", 0)], EDGES, "ZZ01AA0001")
    assert result["rejected_links"][0]["reason"] == "SAME_PLATE_COLLISION"
    result = reconstruct(
        [node("a", "C2", 0), node("b", "C3", 60), node("c", "C4", 65)], EDGES, "ZZ01AA0001"
    )
    assert len(result["inferred_links"]) == 2
    assert all(link["status"] == "ambiguous" for link in result["inferred_links"])
    assert result["alternatives"]


def test_windows_and_percentiles():
    with pytest.raises(ValidationError):
        Window.model_validate(
            {
                "run_id": "00000000-0000-0000-0000-000000000001",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-01T00:00:00Z",
            }
        )
    assert percentile([60, 60, 180, 180], 0.5) == 120
    assert percentile([60, 60, 180, 180], 0.9) == 180


def test_real_mode_fails_without_exposing_configuration_secret():
    from roadeye.config import Settings

    secret = "test-only-sensitive-config"
    with pytest.raises(ValidationError) as error:
        Settings(source_mode="recorded_real", demo_enabled=True, demo_password=secret)
    assert "Real input adapters are unavailable" in str(error.value)
    assert secret not in str(error.value)
