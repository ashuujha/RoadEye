"""Typed public result payloads. Extra metadata is retained for engineering inspection."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict


class Record(BaseModel):
    model_config = ConfigDict(extra="allow")


class HealthData(Record):
    status: str


class HealthResponse(BaseModel):
    data: HealthData


class CameraData(Record):
    id: str
    zone_id: str | None
    name: str
    x: float | None
    y: float | None
    direction: str


class CameraListResponse(BaseModel):
    data: list[CameraData]


class RunData(Record):
    id: str
    scenario: str
    source_mode: Literal["synthetic", "recorded_real"]
    state: Literal["paused", "playing", "delivered"]
    cursor: int
    version: int
    clock: AwareDatetime
    graph: list[dict]


class RunResponse(BaseModel):
    data: RunData


class RunListResponse(BaseModel):
    data: list[RunData]


class Contribution(Record):
    frame_id: str
    raw: str
    normalized: list[str]
    input_score: float


class ConsensusData(Record):
    plate: str | None
    status: Literal["accepted", "review_required", "rejected"]
    score: float
    margin: float
    reasons: list[str]
    policy: str
    contributions: list[Contribution]
    alternatives: list[dict]
    independent_frames: int
    thresholds: dict[str, float]
    score_meaning: str


class ObservationData(Record):
    id: str
    passage_id: str
    run_id: str
    plate: str | None
    status: Literal["accepted", "review_required", "rejected"]
    captured_at: AwareDatetime
    processed_at: AwareDatetime
    machine: ConsensusData
    policy: str
    source_mode: Literal["synthetic", "recorded_real"]
    inference_origin: Literal["mock_candidates", "model_inference"]


class ObservedNode(ObservationData):
    camera_id: str
    lane_id: str
    score: float
    evidence_id: str
    observed: Literal[True]


class ObservationPage(BaseModel):
    items: list[ObservedNode]
    total: int
    offset: int


class ObservationListResponse(BaseModel):
    data: ObservationPage


class ObservationResponse(BaseModel):
    data: ObservationData


class Route(Record):
    cameras: list[str]
    distance_m: int
    baseline_seconds: int


class Link(Record):
    source: str
    target: str
    elapsed_seconds: float
    observed: Literal[False]


class InferredLink(Link):
    routes: list[Route]
    score: float
    status: Literal["plausible", "ambiguous"]


class RejectedLink(Link):
    reason: str


class JourneyData(Record):
    id: str
    run_id: str
    source_mode: Literal["synthetic", "recorded_real"]
    result_version: int
    scoring_policy: str
    window_start: AwareDatetime
    window_end: AwareDatetime
    observed_nodes: list[ObservedNode]
    inferred_links: list[InferredLink]
    rejected_links: list[RejectedLink]
    review_candidates: list[dict]
    alternatives: list[dict]
    missing_coverage: list[dict]
    truncated: bool
    limitations: str


class JourneyResponse(BaseModel):
    data: JourneyData


class CountData(Record):
    camera_id: str
    lane_id: str
    passages: int
    accepted_plates: int
    recognition_coverage: float | None
    count_rate_per_minute: float
    coverage_state: Literal["fresh", "stale"]


class AnalyticsData(Record):
    run_id: str
    source_mode: Literal["synthetic", "recorded_real"]
    window_start: AwareDatetime
    window_end: AwareDatetime
    result_version: int
    status: Literal["provisional", "current_recomputable"]
    basis: str
    sample_size: int
    vehicle_passages: int
    accepted_plates: int
    recognition_coverage: float | None
    review_required: int
    rejected: int
    ocr_pending: int
    counts: list[CountData]
    camera_health: list[dict]
    flow: list[dict]
    od: list[dict]
    travel_times: list[dict]
    ambiguous_links_excluded: int
    limitations: list[str]


class AnalyticsResponse(BaseModel):
    data: AnalyticsData


class AlertData(Record):
    id: str
    run_id: str
    kind: str
    status: Literal["active", "review_required", "acknowledged"]
    observation_id: str | None
    evidence_id: str | None
    details: dict
    created_at: AwareDatetime


class AlertListResponse(BaseModel):
    data: list[AlertData]
