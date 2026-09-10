"""Deployment smoke test for the same-origin Vercel API entrypoint."""

import importlib
import sys

from fastapi.testclient import TestClient

from roadeye.auth import DEMO_PASSWORD_ENV


def test_vercel_entrypoint_supports_login_and_evaluation_data(monkeypatch) -> None:
    password = "deployment-test-password"
    monkeypatch.setenv(DEMO_PASSWORD_ENV, password)
    sys.modules.pop("api.index", None)
    index = importlib.import_module("api.index")

    with TestClient(index.app, base_url="https://roadeye.example") as client:
        assert client.get("/v1/health/ready").status_code == 200
        assert client.get("/v1/auth/me").status_code == 401
        assert client.post(
            "/v1/auth/login",
            json={"actor": "administrator", "password": "incorrect-password"},
        ).status_code == 401

        login = client.post(
            "/v1/auth/login",
            json={"actor": "administrator", "password": password},
        )
        assert login.status_code == 200
        assert login.json()["data"]["actor"] == "administrator"
        assert "HttpOnly" in login.headers["set-cookie"]
        assert "Secure" in login.headers["set-cookie"]
        assert "SameSite=strict" in login.headers["set-cookie"]
        assert client.get("/v1/auth/me").status_code == 200
        assert len(client.get("/v1/demo/runs").json()["data"]) == 1
        assert len(client.get("/v1/cameras").json()["data"]) == 4
        run_id = client.get("/v1/demo/runs").json()["data"][0]["id"]
        map_cameras = client.get(f"/v1/map/cameras?run_id={run_id}").json()["data"]
        assert map_cameras["location_country"] == "United States"
        assert map_cameras["approximate_center"]["longitude"] < 0
        map_trajectories = client.get(
            f"/v1/map/trajectories?run_id={run_id}"
        ).json()["data"]["trajectories"]
        assert len(map_trajectories) == 8

        # Vercel's file-based Python runtime may present the rewritten function
        # path to ASGI; the middleware normalizes it to the existing API contract.
        assert client.get("/api/v1/health/ready").status_code == 200
        assert client.get(
            "/api?__roadeye_path=/v1/health/ready"
        ).status_code == 200


def test_vercel_entrypoint_reports_missing_password_without_crashing(monkeypatch) -> None:
    monkeypatch.delenv(DEMO_PASSWORD_ENV, raising=False)
    index = importlib.import_module("api.index")

    with TestClient(index._create_vercel_app()) as client:
        response = client.get("/v1/health/ready")

    assert response.status_code == 503
    assert DEMO_PASSWORD_ENV in response.json()["detail"]
