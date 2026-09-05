import pytest
from pydantic import ValidationError
from roadeye.recorded.review import LabelRequest, calculate_metrics


def prediction(identity, status="accepted", plate="ZZ00ZZ0001"):
    return {
        "id": identity,
        "observation": {
            "status": status,
            "plate": plate,
            "machine": {"status": status, "plate": plate},
        },
    }


def label(identity=None, **fields):
    return {
        "passage_id": identity,
        "label": {
            "kind": "passage" if identity else "missed_vehicle",
            "passage_assessment": "valid",
            "readability": "readable",
            "plate_detection": "correct",
            "transcription": "ZZ00ZZ0001",
            **fields,
        },
    }


def coverage():
    return label(
        kind="timeline_coverage", confirmed_complete=True, relative_seconds=0, end_seconds=60
    )


def test_incomplete_review_never_claims_accuracy():
    result = calculate_metrics(
        [prediction("a"), prediction("b", "rejected")], [], {"duration_seconds": 60}
    )
    assert result["automatic_acceptance_coverage_predicted"] == 0.5
    assert result["ground_truth_vehicle_passages"] is None
    assert result["readable_only_full_plate_accuracy"] is None
    assert result["known_incorrect_accepted"] is None


def test_misses_duplicates_and_unreadable_remain_in_denominators():
    result = calculate_metrics(
        [prediction("a"), prediction("b"), prediction("c", "rejected")],
        [
            label("a"),
            label("b", passage_assessment="duplicate"),
            label("c", readability="unreadable", transcription=None),
            label(),
            coverage(),
        ],
        {"duration_seconds": 60},
    )
    assert result["evaluation_complete"]
    assert result["ground_truth_vehicle_passages"] == 3
    assert result["missed_vehicles"] == 1
    assert result["readable_only_full_plate_accuracy"] == 0.5
    assert result["correct_full_plate_overall_coverage"] == 1 / 3
    assert result["known_incorrect_accepted"] == 0
    assert result["accepted_invalid_passages_reviewed"] == 1


def test_unresolved_missed_marker_blocks_complete_metrics():
    result = calculate_metrics(
        [prediction("a")],
        [label("a"), label(passage_assessment="uncertain"), coverage()],
        {"duration_seconds": 60},
    )
    assert not result["evaluation_complete"]
    assert result["ground_truth_vehicle_passages"] is None


def test_human_readable_requires_independent_text():
    with pytest.raises(ValidationError):
        LabelRequest(kind="missed_vehicle", reviewer_name="Test", readability="readable")


def test_operational_correction_cannot_inflate_machine_accuracy():
    p = prediction("a", plate="ZZ00ZZ0002")
    p["observation"]["plate"] = "ZZ00ZZ0001"
    result = calculate_metrics([p], [label("a"), coverage()], {"duration_seconds": 60})
    assert result["known_incorrect_accepted"] == 1
    assert result["readable_only_full_plate_accuracy"] == 0
