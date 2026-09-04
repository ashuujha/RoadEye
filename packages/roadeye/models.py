"""Relational ownership and uniqueness; JSON stores immutable contracts and decisions."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from roadeye.db import now


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"))
    name: Mapped[str]
    x: Mapped[float]
    y: Mapped[float]
    direction: Mapped[str] = mapped_column(default="forward")


class Lane(Base):
    __tablename__ = "lanes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"))
    __table_args__ = (UniqueConstraint("id", "camera_id"),)


class Edge(Base):
    __tablename__ = "edges"
    source: Mapped[str] = mapped_column(ForeignKey("cameras.id"), primary_key=True)
    target: Mapped[str] = mapped_column(ForeignKey("cameras.id"), primary_key=True)
    distance_m: Mapped[int]
    min_seconds: Mapped[int]
    max_seconds: Mapped[int]
    baseline_seconds: Mapped[int]
    __table_args__ = (
        CheckConstraint("distance_m > 0 AND min_seconds > 0 AND max_seconds >= min_seconds"),
    )


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    manifest: Mapped[dict] = mapped_column(JSON)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    scenario: Mapped[str]
    source_mode: Mapped[str] = mapped_column(default="synthetic")
    network: Mapped[str] = mapped_column(default="fictional-six")
    state: Mapped[str] = mapped_column(default="paused")
    cursor: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=0)
    clock: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    graph: Mapped[list] = mapped_column(JSON)
    __table_args__ = (CheckConstraint("source_mode = 'synthetic'"),)


class InputEvent(Base):
    __tablename__ = "input_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    event_id: Mapped[str]
    actor: Mapped[str]
    key: Mapped[str]
    digest: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("run_id", "event_id"),
        UniqueConstraint("run_id", "actor", "key"),
    )


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(ForeignKey("input_events.id"), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    state: Mapped[str] = mapped_column(default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None]
    error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("state IN ('pending','leased','done','poison')"),)


class Evidence(Base):
    __tablename__ = "evidence_assets"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    object_key: Mapped[str]
    digest: Mapped[str]
    size: Mapped[int]
    media_type: Mapped[str]
    source_mode: Mapped[str] = mapped_column(default="synthetic")
    __table_args__ = (UniqueConstraint("run_id", "object_key"),)


class Passage(Base):
    __tablename__ = "vehicle_passages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    passage_key: Mapped[str]
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"))
    lane_id: Mapped[str]
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    input_id: Mapped[str] = mapped_column(ForeignKey("input_events.id"), unique=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_assets.id"))
    source_mode: Mapped[str] = mapped_column(default="synthetic")
    __table_args__ = (
        UniqueConstraint("run_id", "camera_id", "passage_key"),
        ForeignKeyConstraint(["lane_id", "camera_id"], ["lanes.id", "lanes.camera_id"]),
        Index("passage_window", "run_id", "camera_id", "captured_at"),
    )


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    passage_id: Mapped[str] = mapped_column(ForeignKey("vehicle_passages.id"), unique=True)
    input_id: Mapped[str] = mapped_column(ForeignKey("input_events.id"), unique=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    plate: Mapped[str | None] = mapped_column(String)
    status: Mapped[str]
    machine: Mapped[dict] = mapped_column(JSON)
    policy: Mapped[str]
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    source_mode: Mapped[str] = mapped_column(default="synthetic")
    inference_origin: Mapped[str] = mapped_column(default="mock_candidates")
    __table_args__ = (Index("plate_time", "run_id", "plate", "captured_at"),)


class OCRReading(Base):
    __tablename__ = "ocr_readings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"))
    frame_id: Mapped[str]
    candidates: Mapped[list] = mapped_column(JSON)
    # Full original duplicated readings remain in immutable input_events.payload.
    __table_args__ = (UniqueConstraint("observation_id", "frame_id"),)


class Revision(Base):
    __tablename__ = "observation_revisions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), index=True)
    number: Mapped[int]
    actor: Mapped[str]
    reason: Mapped[str]
    plate: Mapped[str | None]
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("observation_id", "number"),)


class Journey(Base):
    __tablename__ = "trajectory_queries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    version: Mapped[int]
    query: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    plate: Mapped[str]
    reason: Mapped[str]
    severity: Mapped[str]
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default="draft")
    creator: Mapped[str]
    approver: Mapped[str | None]
    __table_args__ = (CheckConstraint("approver IS NULL OR creator <> approver"),)


class Approval(Base):
    __tablename__ = "watchlist_approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id"))
    actor: Mapped[str]
    action: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    suppression_key: Mapped[str] = mapped_column(unique=True)
    kind: Mapped[str]
    status: Mapped[str]
    observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"))
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_assets.id"))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AlertAction(Base):
    __tablename__ = "alert_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id"))
    actor: Mapped[str]
    classification: Mapped[str]
    notes: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CameraHealth(Base):
    __tablename__ = "camera_health"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), primary_key=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Audit(Base):
    __tablename__ = "audit_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    actor: Mapped[str]
    operation: Mapped[str]
    target: Mapped[str]
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), index=True)
    correlation_id: Mapped[str]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LocalSession(Base):
    __tablename__ = "local_sessions"
    digest: Mapped[str] = mapped_column(String, primary_key=True)
    actor: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Command(Base):
    __tablename__ = "commands"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    actor: Mapped[str]
    operation: Mapped[str]
    key: Mapped[str]
    digest: Mapped[str]
    response: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("actor", "operation", "key"),)
