"""Read-only response mapping for the frozen Karman frontend contract.

This module deliberately adapts the existing prediction demo repository instead
of introducing a second data model.  It does not implement mutable Karman
features (alerts, reviews, watchlists, jobs, or scenario controls).
"""

from __future__ import annotations

import hashlib
import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


_CLOCK_ORIGIN = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)


def _iso_at(seconds: float) -> str:
    value = _CLOCK_ORIGIN + timedelta(seconds=float(seconds))
    return value.isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\0".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


@dataclass(frozen=True)
class EvidenceReference:
    global_id: str
    visit_index: int
    sample_index: int


class FrontendCompatibility:
    """Translate immutable demo predictions into the frontend's read contract."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository
        prediction_hash = repository.run["prediction_sha256"]["journeys"]
        self.run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, prediction_hash))
        self._evidence: dict[str, EvidenceReference] = {}
        self._observations = self._build_observations()
        self._observation_by_id = {
            observation["id"]: observation for observation in self._observations
        }
        self._cameras = self._build_cameras()
        self._edges = self._build_edges()

    def _build_observations(self) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for source in self.repository.journeys:
            journey = self.repository.journey(source["global_id"])
            for visit_index, visit in enumerate(journey["visits"]):
                samples = visit["evidence_samples"]
                if not samples:
                    continue
                sample_index = next(
                    (
                        index
                        for index, candidate in enumerate(samples)
                        if candidate.get("plate_prediction") is not None
                    ),
                    0,
                )
                sample = samples[sample_index]
                evidence_id = _stable_id(
                    "evidence", source["global_id"], visit_index, sample_index
                )
                observation_id = _stable_id(
                    "observation", source["global_id"], visit_index
                )
                self._evidence[evidence_id] = EvidenceReference(
                    source["global_id"], visit_index, sample_index
                )
                plate_prediction = sample.get("plate_prediction")
                plate = (
                    plate_prediction.get("predicted_plate_text")
                    if isinstance(plate_prediction, dict)
                    else None
                )
                score = (
                    float(plate_prediction["ocr_score"])
                    if isinstance(plate_prediction, dict)
                    else float(sample["baseline_score"]["value"])
                )
                score_meaning = (
                    "uncalibrated_ocr_model_score_not_probability"
                    if plate is not None
                    else "uncalibrated_track_score_not_probability"
                )
                captured_at = _iso_at(visit["identified_at_s"])
                reasons = [
                    "runtime_prediction_not_ground_truth",
                    score_meaning,
                ]
                contribution = {
                    "frame_id": str(sample["frame"]),
                    "input_score": score,
                    "normalized": [plate] if plate else [],
                    "raw": plate or "",
                    "candidate": plate,
                    "confidence": score,
                    "quality": None,
                    "bonus": 0,
                    "weight": score,
                }
                machine = {
                    "alternatives": [],
                    "contributions": [contribution],
                    "independent_frames": len(samples),
                    "margin": 0.0,
                    "plate": plate,
                    "policy": "frozen_prediction_unverified",
                    "reasons": reasons,
                    "score": score,
                    "score_meaning": score_meaning,
                    "status": "review_required",
                    "thresholds": {},
                }
                observations.append(
                    {
                        "id": observation_id,
                        "run_id": self.run_id,
                        "passage_id": visit["tracklet_key"],
                        "camera_id": visit["camera"],
                        "lane_id": "unknown",
                        "lane": None,
                        "captured_at": captured_at,
                        "processed_at": captured_at,
                        "plate": plate,
                        "status": "review_required",
                        "score": score,
                        "policy": "frozen_prediction_unverified",
                        "inference_origin": "model_inference",
                        "source_mode": "recorded_real",
                        "observed": True,
                        "evidence_id": evidence_id,
                        "evidence_sha256": sample["crop_sha256"],
                        "passage": {"evidence_id": evidence_id},
                        "machine": machine,
                        "revisions": [],
                        "prediction_status": journey["prediction_status"],
                        "disclosure": journey.get("disclosure"),
                    }
                )
        observations.sort(key=lambda row: (row["captured_at"], row["id"]))
        return observations

    def _build_cameras(self) -> list[dict[str, Any]]:
        positions = self.repository.topology["positions"]
        longitudes = [float(value["longitude"]) for value in positions.values()]
        latitudes = [float(value["latitude"]) for value in positions.values()]
        lon_min, lon_max = min(longitudes), max(longitudes)
        lat_min, lat_max = min(latitudes), max(latitudes)

        def scale(value: float, low: float, high: float, start: float, end: float) -> float:
            if high == low:
                return round((start + end) / 2, 3)
            return round(start + ((value - low) / (high - low)) * (end - start), 3)

        cameras = []
        for camera_id, position in positions.items():
            longitude = float(position["longitude"])
            latitude = float(position["latitude"])
            cameras.append(
                {
                    "id": camera_id,
                    "name": camera_id,
                    "direction": "forward",
                    "zone_id": "approximate_reference_position",
                    "x": scale(longitude, lon_min, lon_max, 65.0, 535.0),
                    "y": scale(latitude, lat_min, lat_max, 215.0, 45.0),
                    "latitude": latitude,
                    "longitude": longitude,
                    "position_status": position.get("kind", self.repository.topology["kind"]),
                    "lanes": [],
                }
            )
        return cameras

    def _build_edges(self) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for source in self.repository.journeys:
            journey = self.repository.journey(source["global_id"])
            visits = journey["visits"]
            for previous, current in zip(visits, visits[1:]):
                link = current.get("incoming_link")
                grouped.setdefault((previous["camera"], current["camera"]), []).append(
                    link or {}
                )
        edges = []
        for (source, target), links in sorted(grouped.items()):
            distances = [float(link["distance_m"]) for link in links if "distance_m" in link]
            gaps = [float(link["temporal_gap_s"]) for link in links if "temporal_gap_s" in link]
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "distance_m": round(statistics.median(distances), 3) if distances else None,
                    "baseline_seconds": round(statistics.median(gaps), 3) if gaps else None,
                    "measurement_status": "predicted_transition_not_observed_route",
                }
            )
        return edges

    def require_run(self, run_id: str) -> None:
        if run_id != self.run_id:
            raise KeyError("Unknown frozen prediction run")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "mode": "local_prediction_demo",
            "runtime_artifact_integrity": "PASS",
        }

    def run(self) -> dict[str, Any]:
        last_time = max(
            (float(visit["last_observed_s"]) for row in self.repository.journeys for visit in row["visits"]),
            default=0.0,
        )
        return {
            "id": self.run_id,
            "scenario": self.repository.config["scenario"],
            "state": "delivered",
            "source_mode": "recorded_real",
            "clock": _iso_at(last_time),
            "cursor": len(self._observations),
            "total_events": len(self._observations),
            "version": 1,
            "graph": self._edges,
            "jobs": {},
            "processing_lag_seconds": 0.0,
            "prediction_status": "UNVERIFIED",
        }

    def runs(self) -> list[dict[str, Any]]:
        return [self.run()]

    def scenarios(self) -> dict[str, Any]:
        scenario = self.repository.config["scenario"]
        return {
            "scenarios": {
                scenario: {
                    "mode": "frozen_read_only_prediction",
                    "scope": self.repository.config["scope"],
                }
            },
            "mutable_runner_available": False,
        }

    def cameras(self) -> list[dict[str, Any]]:
        return self._cameras

    def graph(self) -> dict[str, Any]:
        return {
            "edges": self._edges,
            "position_status": self.repository.topology["kind"],
            "geometry_notice": self.repository.status()["geometry_notice"],
        }

    def observations(self, run_id: str, *, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        self.require_run(run_id)
        return {
            "items": self._observations[offset : offset + limit],
            "offset": offset,
            "total": len(self._observations),
        }

    def observation(self, observation_id: str) -> dict[str, Any]:
        try:
            return self._observation_by_id[observation_id]
        except KeyError as error:
            raise KeyError("Unknown prediction observation") from error

    def evidence_reference(self, evidence_id: str) -> EvidenceReference:
        try:
            return self._evidence[evidence_id]
        except KeyError as error:
            raise KeyError("Unknown prediction evidence") from error

    def analytics(self, run_id: str, *, start: str, end: str) -> dict[str, Any]:
        self.require_run(run_id)
        source = self.repository.analytics()
        summary = source["summary"]
        counts = [
            {
                "camera_id": row["camera"],
                "lane_id": "all",
                "passages": row["observed_runtime_visit_count"],
                "accepted_plates": 0,
                "review_required": row["observed_runtime_visit_count"],
                "recognition_coverage": 0.0,
                "count_rate_per_minute": 0.0,
                "coverage_state": "fresh",
                "measurement_status": row["measurement_status"],
            }
            for row in source["camera_density"]
        ]
        flow = [
            {
                "source": row["from_camera"],
                "target": row["to_camera"],
                "count": row["predicted_transition_count"],
                "median_seconds": row["median_observed_boundary_gap_s"],
                "measurement_status": row["measurement_status"],
            }
            for row in source["bottleneck_proxies"]
        ]
        od = [
            {
                "origin": row["origin_camera"],
                "destination": row["destination_camera"],
                "count": row["predicted_vehicle_count"],
                "measurement_status": row["measurement_status"],
            }
            for row in source["origin_destination_pairs"]
        ]
        total = int(summary["observed_runtime_visits"])
        return {
            "run_id": self.run_id,
            "window_start": start,
            "window_end": end,
            "vehicle_passages": total,
            "accepted_plates": 0,
            "review_required": total,
            "rejected": 0,
            "ocr_pending": sum(row["plate"] is None for row in self._observations),
            "recognition_coverage": 0.0,
            "sample_size": total,
            "counts": counts,
            "flow": flow,
            "od": od,
            "travel_times": [],
            "camera_health": [],
            "ambiguous_links_excluded": 0,
            "basis": "hash_verified_frozen_runtime_predictions",
            "status": "provisional",
            "result_version": 1,
            "source_mode": "recorded_real",
            "limitations": [
                source.get("disclosure") or "Predictions are unverified runtime outputs.",
                "Counts are prediction-only aggregates, not verified traffic volume or density.",
                "Camera boundary gaps are not road travel times or congestion measurements.",
                "Plate text and model scores are predictions, not ground truth or probabilities.",
            ],
            "claim_boundaries": source["claim_boundaries"],
        }

    def trajectory(
        self,
        *,
        run_id: str,
        plate: str,
        include_review: bool,
        limit: int,
    ) -> dict[str, Any]:
        self.require_run(run_id)
        search = self.repository.search_plates(plate, limit=limit)
        base = {
            "result_version": 1,
            "scoring_policy": "frozen_prediction_unverified",
            "query": plate,
            "observed_nodes": [],
            "inferred_links": [],
            "rejected_links": [],
            "review_candidates": [],
            "limitations": search.get("reason")
            or "No runtime OCR prediction matched this query.",
            "plate_search": {
                "availability": search["availability"],
                "prediction_label": search["prediction_label"],
            },
        }
        if not search["results"]:
            return base

        global_id = search["results"][0]["global_id"]
        journey = self.repository.journey(global_id)
        observed_nodes = []
        inferred_links = []
        for visit_index, visit in enumerate(journey["visits"]):
            observation_id = _stable_id("observation", global_id, visit_index)
            observed_nodes.append(self._observation_by_id[observation_id])
            incoming = visit.get("incoming_link")
            if visit_index and incoming is not None:
                inferred_links.append(
                    {
                        "source": journey["visits"][visit_index - 1]["camera"],
                        "target": visit["camera"],
                        "elapsed_seconds": incoming["temporal_gap_s"],
                        "speed_kph": None,
                        "score": incoming["appearance_similarity"],
                        "score_meaning": incoming["score_kind"],
                        "status": "plausible",
                        "observed": False,
                        "routes": [],
                    }
                )
        base.update(
            {
                "global_id": global_id,
                "observed_nodes": observed_nodes,
                "inferred_links": inferred_links,
                "review_candidates": inferred_links if include_review else [],
                "limitations": (
                    "Observed nodes are camera detections. Connections are unverified "
                    "algorithmic associations; straight lines are schematic, and model "
                    "scores are not probabilities."
                ),
                "disclosure": journey.get("disclosure"),
            }
        )
        return base
