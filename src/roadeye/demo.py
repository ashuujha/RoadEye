"""Read-only local demo API over frozen RoadEye prediction artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .s06_demo import S06_DISCLOSURE

ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within(root: Path, relative: str, *, label: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{label} path escapes its allowed root")
    return path


def _bearing_degrees(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Return initial bearing for an explicitly approximate straight segment."""
    lat1, lat2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    delta = math.radians(b["longitude"] - a["longitude"])
    x = math.sin(delta) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
        lat2
    ) * math.cos(delta)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


@dataclass(frozen=True)
class DemoPaths:
    artifacts: Path
    dataset: Path
    frontend: Path


class DemoRepository:
    """Validated view of predictions; it never opens CityFlow identity labels."""

    _RUNTIME_FILES = (
        "prepared.json",
        "run.json",
        "journeys.json",
        "links.json",
        "tracklets.json",
        "topology.json",
    )

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path.resolve()
        config = _json(self.config_path)
        if config.get("schema_version") != 1:
            raise ValueError("Unsupported demo configuration schema")
        if config.get("scenario", "").startswith("S06") and config.get(
            "disclosure"
        ) != S06_DISCLOSURE:
            raise ValueError("S06 demo configuration is missing its disclosure")
        self.config = config
        self.paths = DemoPaths(
            artifacts=_within(
                ROOT, config["runtime_artifacts"], label="runtime artifacts"
            ),
            dataset=_within(ROOT, config["dataset_root"], label="dataset"),
            frontend=_within(ROOT, config["frontend_root"], label="frontend"),
        )
        if not self.paths.frontend.is_dir():
            raise ValueError("Test frontend directory is missing")
        for name in self._RUNTIME_FILES:
            if not (self.paths.artifacts / name).is_file():
                raise ValueError(f"Missing runtime artifact: {name}")

        self.prepared = _json(self.paths.artifacts / "prepared.json")
        self.run = _json(self.paths.artifacts / "run.json")
        self._verify_hashes()
        self.journeys = _json(self.paths.artifacts / "journeys.json")
        self.links = _json(self.paths.artifacts / "links.json")
        self.tracklets = _json(self.paths.artifacts / "tracklets.json")
        self.topology = _json(self.paths.artifacts / "topology.json")
        self._journeys = {row["global_id"]: row for row in self.journeys}
        self._links_to = {row["to_key"]: row for row in self.links}
        if len(self._journeys) != len(self.journeys):
            raise ValueError("Duplicate global vehicle ID in runtime predictions")
        if set(self.topology["positions"]) != {
            visit["camera"]
            for journey in self.journeys
            for visit in journey["visits"]
        }:
            raise ValueError("Journey cameras and topology positions differ")

    def _verify_hashes(self) -> None:
        if _sha256(self.paths.artifacts / "prepared.json") != self.run.get(
            "prepared_sha256"
        ):
            raise ValueError("Runtime artifact hash mismatch: prepared.json")
        expected = {
            "journeys.json": self.run["prediction_sha256"]["journeys"],
            "links.json": self.run["prediction_sha256"]["links"],
            "tracklets.json": self.prepared["artifact_sha256"]["tracklets.json"],
            "topology.json": self.prepared["artifact_sha256"]["topology.json"],
        }
        for name, digest in expected.items():
            if _sha256(self.paths.artifacts / name) != digest:
                raise ValueError(f"Runtime artifact hash mismatch: {name}")

    def status(self) -> dict[str, Any]:
        camera_counts: dict[str, int] = {}
        for journey in self.journeys:
            key = str(journey["camera_count"])
            camera_counts[key] = camera_counts.get(key, 0) + 1
        return {
            "status": self.config.get("claim_status", "PASS"),
            "disclosure": self.config.get("disclosure"),
            "scope": self.config["scope"],
            "runtime_artifact_integrity": "PASS",
            "scenario": self.config["scenario"],
            "vehicle_count": len(self.journeys),
            "predicted_link_count": len(self.links),
            "multi_camera_vehicle_count": sum(
                row["camera_count"] > 1 for row in self.journeys
            ),
            "max_predicted_camera_count": max(
                (row["camera_count"] for row in self.journeys), default=0
            ),
            "camera_count_distribution": camera_counts,
            "camera_positions": self.topology["positions"],
            "position_status": self.topology["kind"],
            "score_notice": (
                "Appearance similarity and baseline scores are uncalibrated "
                "model values, not probabilities."
            ),
            "geometry_notice": (
                "Lines between approximate camera reference points are "
                "interpolated and are not measured road routes."
            ),
            "evaluation_notice": self.config.get(
                "evaluation_notice",
                "Runtime data contains predictions and evidence only; "
                "ground-truth identities are excluded.",
            ),
        }

    def list_vehicles(
        self, query: str = "", *, multi_camera_only: bool = True, limit: int = 50
    ) -> list[dict[str, Any]]:
        needle = query.strip().casefold()
        rows = []
        for journey in self.journeys:
            visits = journey["visits"]
            searchable = " ".join(
                [journey["global_id"]]
                + [visit["tracklet_key"] for visit in visits]
                + [visit["camera"] for visit in visits]
            ).casefold()
            if multi_camera_only and journey["camera_count"] < 2:
                continue
            if needle and needle not in searchable:
                continue
            first_sample = visits[0]["evidence_samples"][0]
            rows.append(
                {
                    "global_id": journey["global_id"],
                    "camera_count": journey["camera_count"],
                    "cameras": [visit["camera"] for visit in visits],
                    "visit_count": len(visits),
                    "first_observed_s": visits[0]["first_observed_s"],
                    "last_observed_s": visits[-1]["last_observed_s"],
                    "representative_crop_url": self._sample_url(
                        journey["global_id"], 0, 0, "crop"
                    ),
                    "representative_tracklet": first_sample["key"],
                    "prediction_status": "predicted_not_runtime_ground_truth",
                    "disclosure": self.config.get("disclosure"),
                }
            )
        rows.sort(
            key=lambda row: (
                -row["camera_count"],
                row["first_observed_s"],
                row["global_id"],
            )
        )
        return rows[:limit]

    def journey(self, global_id: str) -> dict[str, Any]:
        try:
            source = self._journeys[global_id]
        except KeyError as error:
            raise KeyError("Unknown RoadEye vehicle ID") from error
        visits = []
        previous = None
        for index, visit in enumerate(source["visits"]):
            incoming = self._links_to.get(visit["tracklet_key"])
            samples = [
                {
                    "frame": sample["frame"],
                    "time_s": sample["time_s"],
                    "bbox_xywh": sample["bbox_xywh"],
                    "crop_sha256": sample["crop_sha256"],
                    "crop_url": self._sample_url(global_id, index, sample_index, "crop"),
                    "source_frame_url": self._sample_url(
                        global_id, index, sample_index, "frame"
                    ),
                    "baseline_score": {
                        "value": sample["baseline_score"],
                        "kind": sample["score_kind"],
                        "is_probability": False,
                    },
                }
                for sample_index, sample in enumerate(visit["evidence_samples"])
            ]
            row: dict[str, Any] = {
                "sequence": index + 1,
                "tracklet_key": visit["tracklet_key"],
                "camera": visit["camera"],
                "first_observed_s": visit["first_observed_s"],
                "identified_at_s": visit["identified_at_s"],
                "last_observed_s": visit["last_observed_s"],
                "position": {
                    "latitude": visit["reference_position"]["latitude"],
                    "longitude": visit["reference_position"]["longitude"],
                    "kind": visit["reference_position"]["kind"],
                },
                "observation_status": "observed_camera_visit",
                "evidence_samples": samples,
                "incoming_link": self._link_evidence(incoming),
            }
            if previous is not None:
                row["interpolation_from_previous"] = {
                    "status": "inferred_straight_line_not_observed_route",
                    "from_camera": previous["camera"],
                    "to_camera": visit["camera"],
                    "bearing_degrees": _bearing_degrees(
                        previous["reference_position"], visit["reference_position"]
                    ),
                }
            else:
                row["interpolation_from_previous"] = None
            visits.append(row)
            previous = visit
        return {
            "global_id": source["global_id"],
            "camera_count": source["camera_count"],
            "visit_count": len(visits),
            "prediction_status": "predicted_not_runtime_ground_truth",
            "disclosure": self.config.get("disclosure"),
            "geometry_status": source["geometry_status"],
            "visits": visits,
        }

    @staticmethod
    def _sample_url(
        global_id: str, visit_index: int, sample_index: int, kind: str
    ) -> str:
        return (
            f"/api/vehicles/{global_id}/visits/{visit_index}/samples/"
            f"{sample_index}/{kind}"
        )

    @staticmethod
    def _link_evidence(link: dict[str, Any] | None) -> dict[str, Any] | None:
        if link is None:
            return None
        return {
            "from_tracklet": link["from_key"],
            "to_tracklet": link["to_key"],
            "appearance_similarity": link["similarity"],
            "second_best_similarity": link["second_best_similarity"],
            "ambiguity_margin": link["margin"],
            "distance_m": link["distance_m"],
            "temporal_gap_s": link["temporal_gap_s"],
            "temporal_topology_reason": link["reason"],
            "decision_time_s": link["decision_time_s"],
            "score_kind": link["score_kind"],
            "is_probability": False,
            "verification_status": "not_scored_in_runtime",
        }

    def sample(self, global_id: str, visit_index: int, sample_index: int) -> dict:
        try:
            visit = self._journeys[global_id]["visits"][visit_index]
            return visit["evidence_samples"][sample_index]
        except (KeyError, IndexError) as error:
            raise KeyError("Unknown journey evidence sample") from error

    def crop_path(self, global_id: str, visit_index: int, sample_index: int) -> Path:
        sample = self.sample(global_id, visit_index, sample_index)
        path = _within(self.paths.artifacts, sample["crop"], label="crop")
        if not path.is_file() or _sha256(path) != sample["crop_sha256"]:
            raise FileNotFoundError("Evidence crop is missing or changed")
        return path

    def source_frame_jpeg(
        self, global_id: str, visit_index: int, sample_index: int
    ) -> bytes:
        sample = self.sample(global_id, visit_index, sample_index)
        video = _within(self.paths.dataset, sample["video"], label="video")
        if not video.is_file():
            raise FileNotFoundError("Source video is missing")
        capture = cv2.VideoCapture(str(video))
        try:
            capture.set(cv2.CAP_PROP_POS_FRAMES, sample["frame"] - 1)
            ok, image = capture.read()
        finally:
            capture.release()
        if not ok:
            raise FileNotFoundError("Source frame could not be decoded")
        x1, y1, x2, y2 = sample["clipped_xyxy"]
        cv2.rectangle(image, (x1, y1), (x2 - 1, y2 - 1), (33, 201, 151), 4)
        label = f'{sample["camera"]}  frame {sample["frame"]}'
        cv2.putText(
            image,
            label,
            (max(8, x1), max(28, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (33, 201, 151),
            2,
            cv2.LINE_AA,
        )
        encoded, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if not encoded:
            raise RuntimeError("Source frame JPEG encoding failed")
        return buffer.tobytes()


def create_app(config_path: Path = ROOT / "configs/demo.json") -> FastAPI:
    repository = DemoRepository(config_path)
    app = FastAPI(
        title="RoadEye local test interface",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.repository = repository

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return repository.status()

    @app.get("/api/vehicles")
    def vehicles(
        q: str = Query(default="", max_length=160),
        multi_camera_only: bool = True,
        limit: int = Query(default=50, ge=1, le=100),
    ) -> list[dict[str, Any]]:
        return repository.list_vehicles(
            q, multi_camera_only=multi_camera_only, limit=limit
        )

    @app.get("/api/vehicles/{global_id}")
    def journey(global_id: str) -> dict[str, Any]:
        try:
            return repository.journey(global_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/api/vehicles/{global_id}/visits/{visit_index}/samples/{sample_index}/crop"
    )
    def crop(global_id: str, visit_index: int, sample_index: int) -> FileResponse:
        try:
            path = repository.crop_path(global_id, visit_index, sample_index)
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return FileResponse(path, media_type="image/jpeg")

    @app.get(
        "/api/vehicles/{global_id}/visits/{visit_index}/samples/{sample_index}/frame"
    )
    def frame(global_id: str, visit_index: int, sample_index: int) -> Response:
        try:
            image = repository.source_frame_jpeg(global_id, visit_index, sample_index)
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(
            content=image,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    app.mount(
        "/",
        StaticFiles(directory=repository.paths.frontend, html=True),
        name="test_frontend",
    )
    return app
