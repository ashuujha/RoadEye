"""Public contracts; mock candidates are supplied, never inferred from evidence images."""

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Role(StrEnum):
    viewer = "viewer"
    investigator = "investigator"
    administrator = "administrator"
    approver = "approver"


class Candidate(Model):
    text: str = Field(max_length=32)
    confidence: float = Field(ge=0, le=1)


class Reading(Model):
    frame_id: str = Field(min_length=1, max_length=80)
    candidates: list[Candidate] = Field(max_length=8)


class Input(Model):
    schema_version: Literal["1"] = "1"
    event_id: UUID
    run_id: UUID
    kind: Literal["passage", "ocr", "heartbeat"]
    camera_id: str = Field(pattern=r"^(C[1-6]|REAL_C1)$")
    lane_id: str = Field(pattern=r"^(C[1-6]|REAL_C1)-L1$")
    captured_at: AwareDatetime
    passage_id: str = Field(min_length=1, max_length=80)
    readings: list[Reading] = Field(default_factory=list, max_length=16)
    input_confidence: float = Field(default=1, ge=0, le=1)
    quality: float = Field(default=1, ge=0, le=1)
    evidence_key: str = Field(default="plate-card.svg", max_length=128)
    source_mode: Literal["synthetic", "recorded_real"] = "synthetic"
    inference_origin: Literal["mock_candidates", "model_inference"] = "mock_candidates"
    metadata: dict = Field(default_factory=dict)
    dataset_version: Literal["1"] = "1"

    @model_validator(mode="after")
    def coherent(self):
        if (self.source_mode == "synthetic") != (self.inference_origin == "mock_candidates"):
            raise ValueError("Source and inference origin mismatch")
        if (self.camera_id == "REAL_C1") != (self.source_mode == "recorded_real"):
            raise ValueError("Camera source mismatch")
        if self.source_mode == "recorded_real" and not self.metadata:
            raise ValueError("Recorded inference metadata required")
        if self.lane_id != f"{self.camera_id}-L1":
            raise ValueError("Lane does not belong to camera")
        if self.kind != "ocr" and self.readings:
            raise ValueError("Only OCR input contains candidate readings")
        if self.captured_at.utcoffset() != timedelta(0):
            raise ValueError("Capture timestamp must use UTC")
        return self


class Login(Model):
    actor: Role
    password: str = Field(max_length=256)


class RunCreate(Model):
    scenario: str = Field(max_length=64)


class Control(Model):
    action: Literal["play", "pause", "step", "replay", "retry"]


class Window(Model):
    run_id: UUID
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self):
        self.start = self.start.astimezone(timezone.utc)
        self.end = self.end.astimezone(timezone.utc)
        if self.end <= self.start or (self.end - self.start).total_seconds() > 86400:
            raise ValueError("Window must be positive and at most 24 hours")
        return self


class TrajectoryQuery(Window):
    plate: str = Field(min_length=1, max_length=32)
    include_review: bool = False
    limit: int = Field(default=100, ge=1, le=200)


class WatchCreate(Model):
    run_id: UUID
    plate: str = Field(max_length=32)
    reason: str = Field(min_length=4, max_length=500)
    severity: Literal["low", "medium", "high"]
    valid_from: AwareDatetime
    valid_until: AwareDatetime

    @model_validator(mode="after")
    def ordered(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Invalid validity window")
        return self


class Decision(Model):
    classification: Literal["true", "false", "uncertain"]
    notes: str = Field(min_length=4, max_length=500)


class Review(Model):
    plate: str | None = Field(default=None, max_length=32)
    status: Literal["accepted", "review_required", "rejected"]
    reason: str = Field(min_length=4, max_length=500)


class CameraConfig(Model):
    name: str = Field(min_length=1, max_length=80)
    zone_id: str = Field(pattern=r"^Z[1-3]$")
    x: float = Field(ge=0, le=1000)
    y: float = Field(ge=0, le=1000)
    direction: Literal["forward"] = "forward"


class EdgeConfig(Model):
    source: str = Field(pattern=r"^C[1-6]$")
    target: str = Field(pattern=r"^C[1-6]$")
    distance_m: int = Field(gt=0, le=100000)
    min_seconds: int = Field(gt=0, le=3600)
    max_seconds: int = Field(gt=0, le=7200)
    baseline_seconds: int = Field(gt=0, le=3600)

    @model_validator(mode="after")
    def valid(self):
        if (
            self.source == self.target
            or not self.min_seconds <= self.baseline_seconds <= self.max_seconds
        ):
            raise ValueError("Invalid directed edge travel window")
        return self


class Result(Model):
    """Envelope for inspectable domain records; OpenAPI gives stable envelope types."""

    data: dict | list


class Receipt(Model):
    input_id: str
    state: Literal["durably_received"] = "durably_received"
    duplicate: bool


class Clock(Protocol):
    def now(self) -> datetime: ...


class ObservationInputSource(Protocol):
    def readings(self) -> list[Input]: ...


class VehiclePassageSource(Protocol):
    def passages(self) -> list[Input]: ...


class FrameSource(Protocol):
    def next_frame(self) -> tuple[bytes, datetime, str]: ...


class PlateDetector(Protocol):
    def detect(self, frame: bytes) -> list[tuple[int, int, int, int]]: ...


class OCRRecognizer(Protocol):
    def recognize(self, crop: bytes) -> list[Candidate]: ...


class EvidenceStore(Protocol):
    def read(self, key: str) -> bytes: ...
