"""Contract tests for the additive trajectory-map endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from roadeye.auth import LocalAuthService
from roadeye.demo import create_app


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "map-contract-password"


def _authenticated_client() -> TestClient:
    app = create_app(
        ROOT / "deployment" / "demo.json",
        auth_service=LocalAuthService(PASSWORD),
    )
    client = TestClient(app)
    login = client.post(
        "/v1/auth/login",
        json={"actor": "viewer", "password": PASSWORD},
    )
    assert login.status_code == 200
    return client


def test_map_routes_require_existing_authentication() -> None:
    app = create_app(
        ROOT / "deployment" / "demo.json",
        auth_service=LocalAuthService(PASSWORD),
    )
    run_id = app.state.frontend_compatibility.run_id

    with TestClient(app) as client:
        response = client.get(f"/v1/map/cameras?run_id={run_id}")

    assert response.status_code == 401
    assert response.json() == {"detail": "SESSION_REQUIRED"}


def test_map_routes_serve_ordered_runtime_journeys() -> None:
    with _authenticated_client() as client:
        run_id = client.get("/v1/demo/runs").json()["data"][0]["id"]
        cameras_response = client.get(f"/v1/map/cameras?run_id={run_id}")
        trajectories_response = client.get(
            f"/v1/map/trajectories?run_id={run_id}"
        )

    assert cameras_response.status_code == 200
    cameras = cameras_response.json()["data"]
    assert cameras["coordinate_accuracy"] == "APPROXIMATE_NOT_SURVEYED_GPS"
    assert "synthetic representative" in cameras["coordinate_notice"].lower()
    assert cameras["tile_source"]["provider"] == "OpenStreetMap Standard"
    assert cameras["tile_source"]["api_key_required"] is False
    assert [camera["camera_id"] for camera in cameras["cameras"]] == [
        "cam_central",
        "cam_north",
    ]

    assert trajectories_response.status_code == 200
    payload = trajectories_response.json()["data"]
    assert payload["trajectory_geometry"] == (
        "STRAIGHT_LINE_BETWEEN_CAMERA_OBSERVATIONS"
    )
    assert len(payload["trajectories"]) == 1
    trajectory = payload["trajectories"][0]
    assert trajectory["vehicle_id"] == "roadeye_evaluation_vehicle_001"
    assert [point["camera_id"] for point in trajectory["points"]] == [
        "cam_north",
        "cam_central",
    ]
    times = [point["identified_at_s"] for point in trajectory["points"]]
    assert times == sorted(times)
    assert all(
        point["incoming_association"] is None
        or point["incoming_association"]["is_probability"] is False
        for point in trajectory["points"]
    )


def test_map_routes_reject_unknown_runs_and_vehicles() -> None:
    with _authenticated_client() as client:
        run_id = client.get("/v1/demo/runs").json()["data"][0]["id"]
        unknown_run = client.get("/v1/map/cameras?run_id=unknown")
        unknown_vehicle = client.get(
            "/v1/map/trajectories",
            params={"run_id": run_id, "vehicle_id": "unknown"},
        )

    assert unknown_run.status_code == 404
    assert unknown_vehicle.status_code == 404
