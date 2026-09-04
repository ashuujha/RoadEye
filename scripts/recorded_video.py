"""Authenticated recorded-video receipt/status and local human review CSV export."""

import argparse
import csv
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--run")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    load_dotenv()
    with httpx.Client(
        base_url=os.getenv("ROADEYE_API_URL", "http://127.0.0.1:8000"),
        headers={"X-RoadEye": "console"},
        timeout=30,
    ) as client:
        response = client.post(
            "/v1/auth/login",
            json={"actor": "administrator", "password": os.environ["ROADEYE_DEMO_PASSWORD"]},
        )
        response.raise_for_status()
        if args.run:
            if args.replay:
                response = client.post(
                    f"/v1/recorded/runs/{args.run}/replay",
                    headers={"Idempotency-Key": str(uuid4())},
                )
            else:
                response = client.get(f"/v1/recorded/runs/{args.run}")
        else:
            response = client.post(
                "/v1/recorded/runs",
                json={"duration_seconds": args.seconds},
                headers={"Idempotency-Key": str(uuid4())},
            )
        response.raise_for_status()
        result = response.json()["data"]
        print(json.dumps(result, indent=2))
        if args.export:
            response = client.get(f"/v1/recorded/runs/{result['run_id']}/passages")
            response.raise_for_status()
            args.export.parent.mkdir(parents=True, exist_ok=True)
            with args.export.open("w", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "passage_id",
                        "clip_seconds",
                        "original_evidence_id",
                        "machine_plate",
                        "machine_status",
                        "human_plate",
                        "human_readability",
                        "human_notes",
                    ],
                )
                writer.writeheader()
                for item in response.json()["data"]:
                    obs = item["observation"] or {}
                    writer.writerow(
                        {
                            "passage_id": item["id"],
                            "clip_seconds": item["relative_seconds"],
                            "original_evidence_id": item["original_frame_evidence_id"],
                            "machine_plate": obs.get("plate"),
                            "machine_status": obs.get("status", "pending"),
                            "human_plate": "",
                            "human_readability": "unreviewed",
                            "human_notes": "",
                        }
                    )


if __name__ == "__main__":
    main()
