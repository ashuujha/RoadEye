"""Drive actual HTTP endpoints. Output is returned by the backend, never ground truth."""

import argparse
import os
import time
from uuid import uuid4

import httpx
from dotenv import load_dotenv


def run():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="normal_journey")
    parser.add_argument("--no-play", action="store_true")
    args = parser.parse_args()
    with httpx.Client(
        base_url=os.getenv("ROADEYE_API_URL", "http://localhost:8000"),
        headers={"X-RoadEye": "console"},
        timeout=15,
    ) as client:
        response = client.post(
            "/v1/auth/login",
            json={"actor": "administrator", "password": os.environ["ROADEYE_DEMO_PASSWORD"]},
        )
        response.raise_for_status()
        response = client.post(
            "/v1/demo/runs",
            json={"scenario": args.scenario},
            headers={"Idempotency-Key": str(uuid4())},
        )
        response.raise_for_status()
        run_id = response.json()["data"]["id"]
        print(f"Synthetic run: {run_id}")
        if args.no_play:
            return
        client.post(
            f"/v1/demo/runs/{run_id}/control",
            json={"action": "play"},
            headers={"Idempotency-Key": str(uuid4())},
        ).raise_for_status()
        for _ in range(120):
            state = client.get(f"/v1/demo/runs/{run_id}").json()["data"]
            if state["state"] == "delivered" and set(state["jobs"]) == {"done"}:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(f"Processing did not complete: {state}")
        print(
            client.get(
                "/v1/analytics/summary",
                params={
                    "run_id": run_id,
                    "start": "2026-01-15T08:00:00Z",
                    "end": "2026-01-15T09:00:00Z",
                },
            ).json()
        )


if __name__ == "__main__":
    run()
