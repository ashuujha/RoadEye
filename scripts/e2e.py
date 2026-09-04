"""Process-level acceptance using an actual API and a controllable separate worker.

Run against an isolated test database with no other worker; this script manages its worker.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
START, END = "2026-01-15T08:00:00Z", "2026-01-15T09:00:00Z"


def main():
    load_dotenv(ROOT / ".env")
    worker = None
    with httpx.Client(
        base_url=os.getenv("ROADEYE_API_URL", "http://127.0.0.1:8000"),
        headers={"X-RoadEye": "console"},
        timeout=15,
    ) as client:

        def post(path, body):
            response = client.post(path, json=body, headers={"Idempotency-Key": str(uuid4())})
            response.raise_for_status()
            return response.json()["data"]

        def login(actor):
            post(
                "/v1/auth/login", {"actor": actor, "password": os.environ["ROADEYE_DEMO_PASSWORD"]}
            )

        def status(run):
            response = client.get(f"/v1/demo/runs/{run}")
            response.raise_for_status()
            return response.json()["data"]

        def wait(run):
            for _ in range(160):
                result = status(run)
                if result["state"] == "delivered" and set(result["jobs"]) == {"done"}:
                    return result
                time.sleep(0.25)
            raise AssertionError(f"Worker did not complete: {result}")

        def create(name):
            return post("/v1/demo/runs", {"scenario": name})["id"]

        def play(run):
            post(f"/v1/demo/runs/{run}/control", {"action": "play"})

        def metric(run):
            response = client.get(
                "/v1/analytics/summary", params={"run_id": run, "start": START, "end": END}
            )
            response.raise_for_status()
            return response.json()["data"]

        def journey(run):
            return post(
                "/v1/trajectories",
                {"run_id": run, "start": START, "end": END, "plate": "ZZ01AA0001"},
            )

        def start_worker():
            return subprocess.Popen(
                [sys.executable, "-m", "apps.worker.main"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        try:
            login("administrator")
            recovery = create("worker_recovery")
            # Durable receipt without a worker. No data can be processed yet.
            for _ in range(7):
                post(f"/v1/demo/runs/{recovery}/control", {"action": "step"})
            assert status(recovery)["jobs"] == {"pending": 7}, (
                "Run this check without another worker"
            )
            assert metric(recovery)["vehicle_passages"] == 0
            worker = start_worker()
            play(recovery)
            wait(recovery)
            assert metric(recovery)["vehicle_passages"] == 3
            worker.terminate()
            worker.wait(timeout=10)
            # New worker process sees previously committed data and replay creates no new effects.
            worker = start_worker()
            post(f"/v1/demo/runs/{recovery}/control", {"action": "replay"})
            wait(recovery)
            assert metric(recovery)["vehicle_passages"] == 3
            result = journey(recovery)
            assert len(result["observed_nodes"]) == 3 and len(result["inferred_links"]) == 2
            evidence = client.get("/v1/evidence/" + result["observed_nodes"][0]["evidence_id"])
            assert evidence.status_code == 200 and b"SYNTHETIC EVIDENCE" in evidence.content
            for name, expected, reason in [
                ("unreadable_plate", 1, None),
                ("impossible_travel", 2, "IMPOSSIBLE_TRAVEL"),
                ("ambiguous_branch", 3, None),
            ]:
                run = create(name)
                play(run)
                wait(run)
                assert metric(run)["vehicle_passages"] == expected
                if name == "unreadable_plate":
                    assert metric(run)["accepted_plates"] == 0
                elif reason:
                    assert journey(run)["rejected_links"][0]["reason"] == reason
                else:
                    assert journey(run)["alternatives"]
            watch_run = create("watchlist_match")
            watch = post(
                "/v1/watchlists",
                {
                    "run_id": watch_run,
                    "plate": "ZZ01AA0001",
                    "reason": "Process acceptance synthetic watch",
                    "severity": "high",
                    "valid_from": START,
                    "valid_until": END,
                },
            )
            login("approver")
            post(f"/v1/watchlists/{watch['id']}/approve", {})
            login("administrator")
            play(watch_run)
            wait(watch_run)
            alerts = client.get("/v1/alerts", params={"run_id": watch_run}).json()["data"]
            assert len(alerts) == 1 and alerts[0]["status"] == "active"
            post(
                f"/v1/alerts/{alerts[0]['id']}/acknowledge",
                {"classification": "true", "notes": "Verified synthetic scenario"},
            )
            assert (
                client.get("/v1/alerts", params={"run_id": watch_run}).json()["data"][0]["status"]
                == "acknowledged"
            )
            print(
                f"PASS process E2E: durable receipt, worker restart, normal journey, evidence, duplicate replay, unreadable counting, impossible/ambiguous links, approved watchlist and acknowledgement. Recovery run: {recovery}"
            )
        finally:
            if worker and worker.poll() is None:
                worker.terminate()
                worker.wait(timeout=10)


if __name__ == "__main__":
    main()
