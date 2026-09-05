"""Human evaluation only. This module must never be imported by the inference worker."""

import re
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select

from roadeye import models as m
from roadeye import services as s
from roadeye.contracts import Model
from roadeye.recorded.service import task_for


class LabelRequest(Model):
    kind: Literal["passage", "missed_vehicle", "timeline_coverage"]
    target_id: UUID | None = None
    passage_id: UUID | None = None
    relative_seconds: float = Field(default=0, ge=0, le=305)
    end_seconds: float | None = Field(default=None, ge=0, le=305)
    passage_assessment: Literal["valid", "duplicate", "incorrect", "uncertain"] = "uncertain"
    plate_detection: Literal["correct", "incorrect", "missing", "uncertain"] = "uncertain"
    readability: Literal["readable", "partial", "unreadable", "not_assessed"] = "not_assessed"
    transcription: str | None = Field(default=None, max_length=32)
    reviewer_name: str = Field(min_length=2, max_length=80)
    notes: str = Field(default="", max_length=1000)
    confirmed_complete: bool = False

    @model_validator(mode="after")
    def coherent(self):
        if self.kind == "passage" and self.passage_id is None:
            raise ValueError("Passage review requires passage ID")
        if self.kind != "passage" and self.passage_id is not None:
            raise ValueError("Timeline labels cannot impersonate a predicted passage")
        if self.kind == "missed_vehicle" and self.target_id is None:
            raise ValueError("Stable timeline vehicle ID required")
        if self.readability == "readable" and not (
            self.transcription and self.transcription.strip()
        ):
            raise ValueError("Readable plates require independent full transcription")
        if self.readability != "readable" and self.transcription:
            raise ValueError("Use notes for partial characters; do not invent a full plate")
        if self.kind == "timeline_coverage" and (
            self.end_seconds is None or self.end_seconds <= self.relative_seconds
        ):
            raise ValueError("Coverage interval must be positive")
        if self.confirmed_complete and self.kind != "timeline_coverage":
            raise ValueError("Completeness belongs to a timeline review")
        return self


def latest(db, run_id: str) -> list[dict]:
    task_for(db, run_id)
    rows = db.scalars(
        select(m.EvaluationLabel)
        .where(m.EvaluationLabel.run_id == run_id)
        .order_by(m.EvaluationLabel.target, m.EvaluationLabel.revision.desc())
    )
    found = {}
    for row in rows:
        if row.target not in found:
            found[row.target] = s.serialize(row)
    return list(found.values())


def save(db, run_id: str, body: LabelRequest, actor: str) -> dict:
    task = task_for(db, run_id)
    s.require_run(db, run_id, lock=True)
    start, end = task.config.get("start_seconds", 0), task.config["duration_seconds"]
    relative = body.relative_seconds
    if body.kind == "passage":
        passage = db.get(m.Passage, str(body.passage_id))
        if not passage or passage.run_id != run_id:
            raise HTTPException(409, "PASSAGE_RUN_MISMATCH")
        event = db.get(m.InputEvent, passage.input_id)
        assert event
        relative = event.payload["metadata"]["relative_seconds"]
        target = f"passage:{body.passage_id}"
    elif body.kind == "timeline_coverage":
        target = "timeline_coverage"
    else:
        target = f"missed:{body.target_id}"
    if not start <= relative < end or (body.end_seconds is not None and body.end_seconds > end):
        raise HTTPException(422, "LABEL_OUTSIDE_RUN_INTERVAL")
    prior = db.scalar(
        select(m.EvaluationLabel)
        .where(m.EvaluationLabel.run_id == run_id, m.EvaluationLabel.target == target)
        .order_by(m.EvaluationLabel.revision.desc())
        .limit(1)
    )
    row = m.EvaluationLabel(
        run_id=run_id,
        target=target,
        revision=prior.revision + 1 if prior else 1,
        passage_id=str(body.passage_id) if body.passage_id else None,
        actor=actor,
        reviewer_name=body.reviewer_name,
        label=body.model_dump(mode="json") | {"relative_seconds": relative},
    )
    db.add(row)
    db.flush()
    s.audit(
        db,
        actor,
        "evaluation.label_saved",
        row.id,
        run_id,
        details={"target": target, "revision": row.revision},
    )
    return s.serialize(row)


def canonical_transcription(value: str | None) -> str:
    # Evaluation cleanup only; no positional substitutions or OCR corrections.
    return re.sub(r"[\s-]", "", (value or "").upper())


def metrics(db, run_id: str) -> dict:
    task = task_for(db, run_id)
    from roadeye.recorded.service import passages

    return calculate_metrics(passages(db, run_id), latest(db, run_id), task.config)


def calculate_metrics(predictions: list[dict], labels: list[dict], config: dict) -> dict:
    # Evaluate immutable machine output, never investigator-corrected operational revisions.
    predictions = [
        p | {"observation": p["observation"]["machine"] if p["observation"] else None}
        for p in predictions
    ]
    by_passage = {r["passage_id"]: r["label"] for r in labels if r["passage_id"]}
    reviewed = [(p, by_passage[p["id"]]) for p in predictions if p["id"] in by_passage]
    missed_markers = [r["label"] for r in labels if r["label"]["kind"] == "missed_vehicle"]
    markers_decided = all(
        label["passage_assessment"] in ("valid", "incorrect") for label in missed_markers
    )
    missed = [
        r["label"]
        for r in labels
        if r["label"]["kind"] == "missed_vehicle" and r["label"]["passage_assessment"] == "valid"
    ]
    coverage = next((r["label"] for r in labels if r["label"]["kind"] == "timeline_coverage"), None)
    full_timeline = bool(
        coverage
        and coverage["confirmed_complete"]
        and coverage["relative_seconds"] == config.get("start_seconds", 0)
        and coverage["end_seconds"] == config["duration_seconds"]
    )
    decided = (
        markers_decided
        and len(reviewed) == len(predictions)
        and all(label["passage_assessment"] != "uncertain" for _, label in reviewed)
    )
    valid = [(p, label) for p, label in reviewed if label["passage_assessment"] == "valid"]
    readable = [(p, label) for p, label in valid if label["readability"] == "readable"]
    readable_missed = sum(label["readability"] == "readable" for label in missed)
    correct = sum(
        canonical_transcription(p["observation"]["plate"] if p["observation"] else None)
        == canonical_transcription(label["transcription"])
        for p, label in readable
    )
    accepted = [
        p for p in predictions if p["observation"] and p["observation"]["status"] == "accepted"
    ]
    accepted_reviewed = [(p, label) for p, label in reviewed if p in accepted]
    comparable_accepted = [
        (p, label)
        for p, label in accepted_reviewed
        if label["passage_assessment"] == "valid" and label["readability"] == "readable"
    ]
    wrong_accepted = sum(
        canonical_transcription(p["observation"]["plate"])
        != canonical_transcription(label["transcription"])
        for p, label in comparable_accepted
    )
    readable_decided = all(label["readability"] != "not_assessed" for _, label in valid) and all(
        label["readability"] != "not_assessed" for label in missed
    )
    complete = full_timeline and decided and readable_decided
    gt = len(valid) + len(missed) if full_timeline and decided else None
    all_readable = len(readable) + readable_missed
    return {
        "policy": "evaluation-v1",
        "predicted_passages": len(predictions),
        "reviewed_predicted_passages": len(reviewed),
        "review_coverage": len(reviewed) / len(predictions) if predictions else None,
        "timeline_complete_declared": full_timeline,
        "evaluation_complete": complete,
        "ground_truth_vehicle_passages": gt,
        "reported_missed_vehicles": len(missed),
        "missed_vehicles": len(missed) if full_timeline and decided else None,
        "reviewed_duplicates": sum(
            label["passage_assessment"] == "duplicate" for _, label in reviewed
        ),
        "reviewed_incorrect_passages": sum(
            label["passage_assessment"] == "incorrect" for _, label in reviewed
        ),
        "reviewed_plate_detections": {
            k: sum(label["plate_detection"] == k for _, label in valid)
            for k in ["correct", "incorrect", "missing", "uncertain"]
        },
        "reviewed_readability": {
            k: sum(label["readability"] == k for _, label in valid)
            + sum(label["readability"] == k for label in missed)
            for k in ["readable", "partial", "unreadable", "not_assessed"]
        },
        "automatic_acceptance_coverage_predicted": len(accepted) / len(predictions)
        if predictions
        else None,
        "accepted_predictions": len(accepted),
        "accepted_predictions_reviewed": len(accepted_reviewed),
        "accepted_transcriptions_comparable": len(comparable_accepted),
        "accepted_invalid_passages_reviewed": sum(
            label["passage_assessment"] in ("duplicate", "incorrect")
            for _, label in accepted_reviewed
        ),
        "known_incorrect_accepted": wrong_accepted if comparable_accepted else None,
        "correct_full_plate_readings_reviewed": correct if readable else None,
        "readable_only_full_plate_accuracy": correct / all_readable
        if complete and all_readable
        else None,
        "correct_full_plate_overall_coverage": correct / gt if complete and gt else None,
        "readable_rejected_or_reviewed": sum(
            not p["observation"] or p["observation"]["status"] != "accepted" for p, _ in readable
        ),
        "denominators": {
            "readable_only": "all human-readable unique vehicles, including misses, in fully reviewed interval",
            "overall": "all human-counted unique crossings, including partial/unreadable/missed",
            "acceptance": "all predicted passages, before duplicate correction",
        },
        "limitations": "Human declarations are not adjudicated truth. Partial reviewed counts are not whole-run accuracy. Labels never change machine output.",
    }
