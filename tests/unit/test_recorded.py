from datetime import datetime, timedelta, timezone
from fractions import Fraction
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from roadeye.contracts import Input
from roadeye.recorded.inference import Tracker, iou
from roadeye.recorded.processing import relative_time


def test_pts_uses_presentation_time_and_assigned_anchor():
    # Neither decode index nor receipt time defines the historical timestamp.
    seconds = relative_time(SimpleNamespace(pts=13440), 640, Fraction(1, 12800))
    assert seconds == 1
    anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert anchor + timedelta(seconds=seconds) == datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="PTS_MISSING"):
        relative_time(SimpleNamespace(pts=None), 0, Fraction(1, 25))


def test_tracker_crosses_once_without_ocr_and_does_not_count_initial_presence():
    tracker = Tracker(300)
    for i, bottom in enumerate([260, 290, 310, 330, 345]):
        tracker.update(
            [{"box": [100, bottom - 150, 300, bottom], "score": 0.8, "class": 2}], i * 0.2, i * 2560
        )
    tracks = list(tracker.tracks.values())
    assert len(tracks) == 1 and tracks[0]["crossed"]
    assert tracks[0]["crossing"]["seconds"] == 0.4
    assert tracks[0]["samples"] == []
    initially_below = Tracker(300)
    initially_below.update([{"box": [100, 200, 300, 350]}], 0, 0)
    assert not next(iter(initially_below.tracks.values()))["crossed"]
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0


def test_provenance_pairing_cannot_claim_mock_is_real():
    payload = dict(
        event_id=uuid4(),
        run_id=uuid4(),
        kind="passage",
        camera_id="REAL_C1",
        lane_id="REAL_C1-L1",
        captured_at=datetime.now(timezone.utc),
        passage_id="t",
        source_mode="recorded_real",
        metadata={"relative_seconds": 0},
    )
    with pytest.raises(ValidationError):
        Input(**payload)
    assert Input(**payload, inference_origin="model_inference").source_mode == "recorded_real"
