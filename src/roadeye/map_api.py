"""Read-only map API over hash-verified RoadEye journey predictions."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .auth import AuthSession

OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">'
    "OpenStreetMap</a> contributors"
)
COORDINATE_NOTICE = (
    "CityFlow camera coordinates are calibration-derived representative road "
    "points, not surveyed camera GPS locations."
)


def _coordinate_notice(repository: Any) -> str:
    if str(repository.config.get("scope", "")).startswith("synthetic_"):
        return (
            "This deployment uses synthetic representative camera coordinates; "
            "they are not real camera locations."
        )
    return COORDINATE_NOTICE


def _valid_coordinate(latitude: float, longitude: float) -> bool:
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    )


def _camera_rows(repository: Any) -> list[dict[str, Any]]:
    synthetic = str(repository.config.get("scope", "")).startswith("synthetic_")
    cameras: list[dict[str, Any]] = []
    for camera_id, source in sorted(repository.topology["positions"].items()):
        latitude = float(source["latitude"])
        longitude = float(source["longitude"])
        if not _valid_coordinate(latitude, longitude):
            raise ValueError(f"Camera {camera_id} has an invalid map coordinate")
        cameras.append(
            {
                "camera_id": camera_id,
                "label": f"Camera {camera_id}",
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_status": source.get(
                    "kind", "approximate_representative_position"
                ),
                "location_description": (
                    "Synthetic representative position"
                    if synthetic
                    else "Representative CityFlow road reference"
                ),
            }
        )
    return cameras


def _predicted_plate(visits: list[dict[str, Any]]) -> str | None:
    for visit in visits:
        for sample in visit.get("evidence_samples", []):
            prediction = sample.get("plate_prediction")
            if isinstance(prediction, dict):
                plate = prediction.get("predicted_plate_text")
                if isinstance(plate, str) and plate:
                    return plate
    return None


def _trajectory_row(journey: dict[str, Any]) -> dict[str, Any]:
    ordered_visits = sorted(
        journey["visits"],
        key=lambda visit: (float(visit["identified_at_s"]), visit["camera"]),
    )
    points = []
    for sequence, visit in enumerate(ordered_visits):
        position = visit["position"]
        latitude = float(position["latitude"])
        longitude = float(position["longitude"])
        if not _valid_coordinate(latitude, longitude):
            raise ValueError(
                f"Journey {journey['global_id']} has an invalid map coordinate"
            )
        incoming = visit.get("incoming_link")
        points.append(
            {
                "sequence": sequence,
                "camera_id": visit["camera"],
                "latitude": latitude,
                "longitude": longitude,
                "first_observed_s": float(visit["first_observed_s"]),
                "identified_at_s": float(visit["identified_at_s"]),
                "last_observed_s": float(visit["last_observed_s"]),
                "coordinate_status": position.get(
                    "kind", "approximate_representative_position"
                ),
                "incoming_association": (
                    {
                        "score": float(incoming["appearance_similarity"]),
                        "score_kind": incoming["score_kind"],
                        "is_probability": False,
                    }
                    if incoming is not None
                    else None
                ),
            }
        )
    return {
        "vehicle_id": journey["global_id"],
        "predicted_plate": _predicted_plate(ordered_visits),
        "camera_count": len({point["camera_id"] for point in points}),
        "point_count": len(points),
        "prediction_status": journey.get("prediction_status", "UNVERIFIED"),
        "geometry_status": journey.get(
            "geometry_status", "observations_only_no_road_route_claim"
        ),
        "disclosure": journey.get("disclosure"),
        "points": points,
    }


def create_map_router(
    *,
    repository: Any,
    run_id: str,
    require_session: Callable[..., AuthSession],
) -> APIRouter:
    """Create additive map routes without changing existing API contracts."""

    router = APIRouter(prefix="/v1/map", tags=["trajectory-map"])

    def require_run(requested_run_id: str) -> None:
        if requested_run_id != run_id:
            raise HTTPException(status_code=404, detail="Unknown frozen prediction run")

    @router.get("/cameras")
    def map_cameras(
        response: Response,
        run_id: str,
        _session: AuthSession = Depends(require_session),
    ) -> dict[str, Any]:
        require_run(run_id)
        try:
            cameras = _camera_rows(repository)
            configured_center = repository.config.get("approximate_center")
            if configured_center is not None:
                center = {
                    "latitude": float(configured_center["latitude"]),
                    "longitude": float(configured_center["longitude"]),
                    "source": configured_center.get(
                        "source", "deployment configuration"
                    ),
                }
                if not _valid_coordinate(center["latitude"], center["longitude"]):
                    raise ValueError("Invalid approximate scenario center")
            elif cameras:
                center = {
                    "latitude": sum(camera["latitude"] for camera in cameras)
                    / len(cameras),
                    "longitude": sum(camera["longitude"] for camera in cameras)
                    / len(cameras),
                    "source": "mean of representative camera road-reference points",
                }
            else:
                raise ValueError("No camera positions are available for the map")
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        response.headers["Cache-Control"] = "private, max-age=300"
        return {
            "data": {
                "run_id": run_id,
                "scenario": repository.config["scenario"],
                "location_label": repository.config.get(
                    "location_label", "Approximate CityFlow scenario area"
                ),
                "location_country": repository.config.get("location_country"),
                "approximate_center": center,
                "coordinate_accuracy": "APPROXIMATE_NOT_SURVEYED_GPS",
                "coordinate_notice": _coordinate_notice(repository),
                "tile_source": {
                    "provider": "OpenStreetMap Standard",
                    "url": OSM_TILE_URL,
                    "attribution": OSM_ATTRIBUTION,
                    "api_key_required": False,
                },
                "cameras": cameras,
            }
        }

    @router.get("/trajectories")
    def map_trajectories(
        response: Response,
        run_id: str,
        vehicle_id: str | None = Query(default=None, max_length=160),
        multi_camera_only: bool = True,
        limit: int = Query(default=200, ge=1, le=500),
        _session: AuthSession = Depends(require_session),
    ) -> dict[str, Any]:
        require_run(run_id)
        if vehicle_id is not None:
            try:
                sources = [repository.journey(vehicle_id)]
            except KeyError as error:
                raise HTTPException(status_code=404, detail=str(error)) from error
        else:
            sources = [
                repository.journey(source["global_id"])
                for source in repository.journeys
                if not multi_camera_only or int(source["camera_count"]) > 1
            ]
            sources = sources[:limit]
        try:
            trajectories = [_trajectory_row(journey) for journey in sources]
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        response.headers["Cache-Control"] = "private, max-age=60"
        return {
            "data": {
                "run_id": run_id,
                "scenario": repository.config["scenario"],
                "coordinate_accuracy": "APPROXIMATE_NOT_SURVEYED_GPS",
                "coordinate_notice": _coordinate_notice(repository),
                "trajectory_geometry": "STRAIGHT_LINE_BETWEEN_CAMERA_OBSERVATIONS",
                "ordering": "identified_at_s_ascending",
                "prediction_status": "UNVERIFIED",
                "trajectories": trajectories,
            }
        }

    return router
