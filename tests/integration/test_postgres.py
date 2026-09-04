import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from roadeye import jobs
from roadeye import models as m
from roadeye import services as s
from roadeye.config import settings
from roadeye.db import SessionLocal, engine, now
from sqlalchemy import select, text

from apps.api.main import app

HEADERS = {"X-RoadEye": "console"}
START = "2026-01-15T08:00:00Z"
END = "2026-01-15T09:00:00Z"


@pytest.fixture
def client():
    with engine.connect() as db:
        assert db.scalar(text("SELECT postgis_lib_version()"))
    with TestClient(app) as client:
        client.headers.update(HEADERS)
        login(client, "administrator")
        yield client


def login(client, actor):
    response = client.post(
        "/v1/auth/login", json={"actor": actor, "password": settings.demo_password}
    )
    assert response.status_code == 200, response.text


def post(client, path, body, key=None):
    response = client.post(path, json=body, headers={"Idempotency-Key": key or str(uuid4())})
    assert response.status_code in (200, 202), response.text
    return response.json().get("data", response.json())


def make_run(client, scenario, play=True):
    run = post(client, "/v1/demo/runs", {"scenario": scenario})
    if play:
        post(client, f"/v1/demo/runs/{run['id']}/control", {"action": "play"})
    return run["id"]


def drain():
    for _ in range(500):
        scheduled = jobs.schedule()
        claimed = jobs.claim(now() + timedelta(minutes=10))
        if claimed:
            jobs.handle(*claimed)
        if not scheduled and not claimed:
            return
    pytest.fail("Worker did not quiesce")


def metrics(client, run_id, end=END):
    response = client.get(
        "/v1/analytics/summary", params={"run_id": run_id, "start": START, "end": end}
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def query(client, run_id):
    return post(
        client,
        "/v1/trajectories",
        {"run_id": run_id, "start": START, "end": END, "plate": "ZZ01AA0001"},
    )


@pytest.mark.parametrize(
    "scenario", list(json.loads((s.DATA / "manifest.json").read_text())["scenarios"])
)
def test_scenario_outcomes(client, scenario):
    run_id = make_run(client, scenario)
    drain()
    expected = json.loads((s.DATA / "ground_truth" / f"{scenario}.json").read_text())
    actual = metrics(client, run_id)
    assert actual["vehicle_passages"] == expected["passages"]
    assert actual["accepted_plates"] == expected["accepted"]
    assert actual["review_required"] == expected["review_required"]
    assert actual["rejected"] == expected["rejected"]
    status = client.get(f"/v1/demo/runs/{run_id}").json()["data"]
    assert set(status["jobs"]) == {"done"}, client.get("/v1/jobs", params={"run_id": run_id}).json()
    if scenario == "normal_journey":
        result = query(client, run_id)
        assert [(x["source"], x["target"]) for x in result["inferred_links"]] == [
            ("C1", "C2"),
            ("C2", "C3"),
        ]
        assert actual["od"] == [
            {"enrolled_origin": "C1", "enrolled_destination": "C3", "sessions": 1}
        ]
        assert metrics(client, run_id, "2026-01-15T08:01:00Z")["vehicle_passages"] == 1
        assert (
            client.get("/v1/evidence/" + result["observed_nodes"][0]["evidence_id"]).status_code
            == 200
        )
    if scenario == "ambiguous_branch":
        result = query(client, run_id)
        assert len(result["inferred_links"]) == 2
        assert result["alternatives"]
        assert actual["flow"] == []
    if scenario in ("impossible_travel", "plate_collision"):
        reason = "IMPOSSIBLE_TRAVEL" if scenario == "impossible_travel" else "SAME_PLATE_COLLISION"
        assert query(client, run_id)["rejected_links"][0]["reason"] == reason
        assert reason in [
            a["kind"] for a in client.get("/v1/alerts", params={"run_id": run_id}).json()["data"]
        ]
    if scenario == "camera_outage":
        assert [h["camera_id"] for h in actual["camera_health"] if h["state"] == "stale"] == ["C6"]
        assert any(
            a["kind"] == "CAMERA_STALE"
            for a in client.get("/v1/alerts", params={"run_id": run_id}).json()["data"]
        )
    if scenario == "congestion_proxy":
        travel = actual["travel_times"][0]
        assert (
            travel["sample_size"],
            travel["median_seconds"],
            travel["p90_seconds"],
            travel["congestion_proxy_ratio"],
        ) == (4, 120, 180, 2)


def test_duplicate_concurrency_conflict_and_replay(client):
    run_id = make_run(client, "watchlist_match", False)
    payload = {
        **next(e for e in s.scenario_events("watchlist_match") if e["kind"] == "passage"),
        "run_id": run_id,
    }
    cookie = dict(client.cookies)

    def ingest(_):
        with TestClient(app) as concurrent:
            concurrent.cookies.update(cookie)
            return concurrent.post(
                "/v1/inputs", json=payload, headers={**HEADERS, "Idempotency-Key": "same"}
            )

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(ingest, range(12)))
    assert all(r.status_code == 202 for r in results), [r.text for r in results]
    assert sum(not r.json()["duplicate"] for r in results) == 1
    bad = client.post(
        "/v1/inputs", json={**payload, "quality": 0.5}, headers={"Idempotency-Key": "same"}
    )
    assert bad.status_code == 409
    drain()
    assert metrics(client, run_id)["vehicle_passages"] == 1
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "replay"})
    drain()
    assert metrics(client, run_id)["vehicle_passages"] == 1


def test_lease_reclaim_idempotent_handler_poison_and_restart(client):
    run_id = make_run(client, "worker_recovery", False)
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "step"})
    lease = jobs.claim()
    assert lease
    engine.dispose()  # New connections must see durable receipt and lease.
    assert jobs.claim() is None
    replacement = jobs.claim(now() + timedelta(seconds=settings.lease_seconds + 1))
    assert replacement and replacement[0] == lease[0] and replacement[1] != lease[1]
    assert not jobs.handle(*lease)
    assert jobs.handle(*replacement)
    assert not jobs.handle(*replacement)
    # An OCR event whose passage never arrives retries, then becomes poison.
    payload = {
        **next(e for e in s.scenario_events("worker_recovery") if e["kind"] == "ocr"),
        "run_id": run_id,
    }
    receipt = post(client, "/v1/inputs", payload)
    for _ in range(settings.max_attempts):
        claimed = jobs.claim(now() + timedelta(minutes=10))
        assert claimed and not jobs.handle(*claimed)
    with SessionLocal() as db:
        assert db.get(m.Job, receipt["input_id"]).state == "poison"
    passage = {
        **next(e for e in s.scenario_events("worker_recovery") if e["kind"] == "passage"),
        "run_id": run_id,
    }
    post(client, "/v1/inputs", passage)
    drain()
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "retry"})
    drain()
    assert metrics(client, run_id)["accepted_plates"] == 1


def test_late_version_and_review_preserve_machine(client):
    run_id = make_run(client, "late_arrival", False)
    # Initial six heartbeats plus C1 and C3. C2 arrives later.
    for _ in range(10):
        post(client, f"/v1/demo/runs/{run_id}/control", {"action": "step"})
        drain()
    first = query(client, run_id)
    assert len(first["observed_nodes"]) == 2
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "play"})
    drain()
    second = query(client, run_id)
    assert second["result_version"] > first["result_version"]
    assert [n["camera_id"] for n in second["observed_nodes"]] == ["C1", "C2", "C3"]
    saved = client.get("/v1/trajectories/" + first["id"]).json()["data"]
    assert saved["stale"] and len(saved["result"]["observed_nodes"]) == 2
    obs_id = second["observed_nodes"][0]["id"]
    post(
        client,
        f"/v1/observations/{obs_id}/reviews",
        {"status": "rejected", "reason": "Synthetic manual review", "plate": None},
    )
    inspected = client.get("/v1/observations/" + obs_id).json()["data"]
    assert inspected["machine"]["status"] == "accepted"
    assert inspected["revisions"][0]["status"] == "rejected"
    assert metrics(client, run_id)["accepted_plates"] == 2


def test_watchlist_roles_validity_suppression_and_audit(client):
    run_id = make_run(client, "watchlist_match", False)
    body = {
        "run_id": run_id,
        "plate": "ZZ01AA0001",
        "reason": "Synthetic watchlist demonstration",
        "severity": "medium",
        "valid_from": START,
        "valid_until": END,
    }
    watch = post(client, "/v1/watchlists", body)
    denied = client.post(f"/v1/watchlists/{watch['id']}/approve", headers={"Idempotency-Key": "x"})
    assert denied.status_code == 403
    login(client, "approver")
    post(client, f"/v1/watchlists/{watch['id']}/approve", {})
    login(client, "administrator")
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "play"})
    drain()
    alerts = client.get("/v1/alerts", params={"run_id": run_id}).json()["data"]
    assert len(alerts) == 1 and alerts[0]["status"] == "active" and alerts[0]["evidence_id"]
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "replay"})
    drain()
    assert len(client.get("/v1/alerts", params={"run_id": run_id}).json()["data"]) == 1
    post(
        client,
        f"/v1/alerts/{alerts[0]['id']}/acknowledge",
        {"classification": "true", "notes": "Matches synthetic scenario"},
    )
    assert any(
        a["operation"] == "alert.acknowledged"
        for a in client.get("/v1/audit", params={"run_id": run_id}).json()["data"]
    )
    login(client, "viewer")
    assert (
        client.get(
            "/v1/observations", params={"run_id": run_id, "start": START, "end": END}
        ).status_code
        == 403
    )
    assert client.get("/v1/evidence/" + alerts[0]["evidence_id"]).status_code == 403
    assert (
        client.get(
            "/v1/analytics/summary", params={"run_id": run_id, "start": START, "end": END}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/v1/demo/runs",
            json={"scenario": "normal_journey"},
            headers={"Idempotency-Key": "viewer"},
        ).status_code
        == 403
    )


def test_scope_provenance_and_evidence_failures(client, tmp_path):
    first = make_run(client, "normal_journey")
    second = make_run(client, "unreadable_plate")
    drain()
    assert len(query(client, first)["observed_nodes"]) == 3
    assert query(client, second)["observed_nodes"] == []
    payload = {
        **s.scenario_events("normal_journey")[0],
        "run_id": first,
        "source_mode": "live_real",
    }
    assert (
        client.post("/v1/inputs", json=payload, headers={"Idempotency-Key": "real"}).status_code
        == 422
    )
    payload.update(source_mode="synthetic", evidence_key="../manifest.json", event_id=str(uuid4()))
    assert (
        client.post(
            "/v1/inputs", json=payload, headers={"Idempotency-Key": "traversal"}
        ).status_code
        == 422
    )
    evidence_id = query(client, first)["observed_nodes"][0]["evidence_id"]
    original = settings.evidence_root
    try:
        settings.evidence_root = tmp_path
        assert client.get("/v1/evidence/" + evidence_id).status_code == 404
    finally:
        settings.evidence_root = original


def test_invalid_windows_idempotent_commands_and_watch_expiry(client):
    command_key = str(uuid4())
    first = post(client, "/v1/demo/runs", {"scenario": "normal_journey"}, command_key)
    second = post(client, "/v1/demo/runs", {"scenario": "normal_journey"}, command_key)
    assert first["id"] == second["id"]
    assert (
        client.post(
            "/v1/demo/runs",
            json={"scenario": "unreadable_plate"},
            headers={"Idempotency-Key": command_key},
        ).status_code
        == 409
    )
    assert (
        client.get(
            "/v1/analytics/summary", params={"run_id": first["id"], "start": END, "end": START}
        ).status_code
        == 422
    )
    run_id = make_run(client, "watchlist_match", False)
    watch = post(
        client,
        "/v1/watchlists",
        {
            "run_id": run_id,
            "plate": "ZZ01AA0001",
            "reason": "Expired synthetic entry",
            "severity": "low",
            "valid_from": "2026-01-15T07:00:00Z",
            "valid_until": START,
        },
    )
    login(client, "approver")
    post(client, f"/v1/watchlists/{watch['id']}/approve", {})
    login(client, "administrator")
    post(client, f"/v1/demo/runs/{run_id}/control", {"action": "play"})
    drain()
    assert client.get("/v1/alerts", params={"run_id": run_id}).json()["data"] == []


def test_database_immutability_and_heartbeat_interval_union(client):
    from sqlalchemy.exc import DBAPIError

    run_id = make_run(client, "normal_journey")
    drain()
    with SessionLocal() as db:
        event_id = db.scalar(select(m.InputEvent.id).where(m.InputEvent.run_id == run_id))
    for statement, params in [
        ("UPDATE runs SET network = :value WHERE id = :id", {"value": "other", "id": run_id}),
        (
            "UPDATE input_events SET actor = :value WHERE id = :id",
            {"value": "other", "id": event_id},
        ),
    ]:
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(text(statement), params)
    camera = metrics(client, run_id)["camera_health"][0]
    assert camera["heartbeat_covered_seconds"] == 240
    assert camera["heartbeat_coverage_fraction"] == pytest.approx(240 / 3600)
