"""Actual-model PostgreSQL/HTTP crash, replay and evidence acceptance. No other worker may run."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import av
import cv2
import httpx
import numpy as np
from dotenv import load_dotenv


def main():
    load_dotenv()
    worker = None
    started = time.monotonic()
    report = {}
    with httpx.Client(
        base_url="http://127.0.0.1:8000", headers={"X-RoadEye": "console"}, timeout=30
    ) as client:

        def post(path, body=None, key=None):
            response = client.post(
                path, json=body, headers={"Idempotency-Key": key or str(uuid4())}
            )
            response.raise_for_status()
            return response.json()["data"]

        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response.json()["data"]

        def spawn():
            return subprocess.Popen(
                [sys.executable, "-m", "apps.worker.main"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        def wait(run_id):
            for _ in range(240):
                result = get(f"/v1/recorded/runs/{run_id}")
                if result["state"] == "failed":
                    raise AssertionError(result["error"])
                if result["state"] == "completed":
                    return result
                time.sleep(0.5)
            raise TimeoutError("Recorded job did not complete within 120 seconds")

        post(
            "/v1/auth/login",
            {"actor": "administrator", "password": os.environ["ROADEYE_DEMO_PASSWORD"]},
        )
        key = str(uuid4())
        created = post("/v1/recorded/runs", {"duration_seconds": 60}, key)
        assert created == post("/v1/recorded/runs", {"duration_seconds": 60}, key)
        conflict = client.post(
            "/v1/recorded/runs", json={"duration_seconds": 30}, headers={"Idempotency-Key": key}
        )
        assert conflict.status_code == 409
        run_id = created["run_id"]
        report["run_id"] = run_id
        assert get(f"/v1/recorded/runs/{run_id}")["state"] == "received"
        try:
            worker = spawn()
            for _ in range(120):
                progress = get(f"/v1/recorded/runs/{run_id}")["progress"]
                if progress.get("published_passages", 0) >= 3:
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("No durable partial publications before crash")
            worker.kill()
            worker.wait(timeout=5)
            report["crashed_after_progress"] = progress
            print(
                json.dumps(
                    {"check": "worker_killed_after_durable_publication", "progress": progress}
                ),
                flush=True,
            )
            worker = spawn()
            result = wait(run_id)
            first = get(f"/v1/recorded/runs/{run_id}/passages")
            assert result["attempts"] == 2 and result["pending_outcomes"] == 0
            assert result["vehicle_passages"] == len(first) > 0
            assert all(
                p["observation"]["source_mode"] == "recorded_real"
                and p["observation"]["inference_origin"] == "model_inference"
                for p in first
            )
            assert run_id not in [r["id"] for r in get("/v1/demo/runs")]
            print(
                json.dumps(
                    {
                        "check": "restart_recovered",
                        "passages": len(first),
                        "outcomes": result["outcomes"],
                    }
                ),
                flush=True,
            )
            before_ids = [(p["id"], p["observation"]["id"]) for p in first]
            post(f"/v1/recorded/runs/{run_id}/replay")
            replay = wait(run_id)
            after = get(f"/v1/recorded/runs/{run_id}/passages")
            assert [(p["id"], p["observation"]["id"]) for p in after] == before_ids
            assert replay["outcomes"] == result["outcomes"] and replay["jobs"] == result["jobs"]
            evidence_ids = {p["original_frame_evidence_id"] for p in after}
            for p in after:
                for sample in p["inference"]["samples"]:
                    assert sample["plate_box"][1] >= 45
                    evidence_ids.update([sample["crop_evidence_id"], sample["frame_evidence_id"]])
            evidence_bytes = {}
            for identity in evidence_ids:
                response = client.get("/v1/evidence/" + identity)
                evidence_bytes[identity] = response.content
                assert response.status_code == 200 and response.headers["content-type"] in (
                    "image/jpeg",
                    "image/png",
                )
            # Compare lossless crop pixels directly with decoded source at the stored PTS.
            samples_by_pts = {}
            anchor = datetime.fromisoformat(result["config"]["replay_anchor"])
            for passage in after:
                assert datetime.fromisoformat(passage["assigned_timestamp"]) == anchor + timedelta(
                    seconds=passage["relative_seconds"]
                )
                for sample in passage["inference"]["samples"]:
                    samples_by_pts.setdefault(sample["pts"], []).append(sample)
            checked_crops = 0
            with av.open(result["config"]["manifest"]["path"]) as source:
                stream = source.streams.video[0]
                for frame in source.decode(stream):
                    seconds = float((frame.pts - (stream.start_time or 0)) * stream.time_base)
                    if seconds >= 60:
                        break
                    for sample in samples_by_pts.get(frame.pts, []):
                        assert abs(seconds - sample["relative_seconds"]) < 1e-9
                        x1, y1, x2, y2 = sample["plate_box"]
                        expected = frame.to_ndarray(format="bgr24")[y1:y2, x1:x2]
                        actual = cv2.imdecode(
                            np.frombuffer(evidence_bytes[sample["crop_evidence_id"]], np.uint8),
                            cv2.IMREAD_COLOR,
                        )
                        assert np.array_equal(expected, actual), (
                            "Crop coordinates/PTS/pixels mismatch"
                        )
                        checked_crops += 1
            assert checked_crops == sum(len(p["inference"]["samples"]) for p in after) > 0
            assert any(
                not p["inference"]["samples"] and p["observation"]["status"] == "rejected"
                for p in after
            )
            report["lossless_crop_pts_checks"] = checked_crops
            post(
                "/v1/auth/login",
                {"actor": "viewer", "password": os.environ["ROADEYE_DEMO_PASSWORD"]},
            )
            assert client.get("/v1/evidence/" + next(iter(evidence_ids))).status_code == 403
            report.update(
                status=result,
                replay=replay,
                evidence_objects_verified=len(evidence_ids),
                missing_evidence=0,
                checks="receipt conflict, crash recovery, duplicate identities/totals, provenance isolation, ROI mapping, authorized JPEG/PNG evidence, viewer denial passed",
                wall_seconds=round(time.monotonic() - started, 3),
            )
            Path(".runtime/recorded-inspection/acceptance.json").write_text(
                json.dumps(report, indent=2)
            )
            print(
                json.dumps(
                    {
                        "checks": report["checks"],
                        "run_id": run_id,
                        "evidence_objects_verified": len(evidence_ids),
                        "wall_seconds": report["wall_seconds"],
                    }
                ),
                flush=True,
            )
        finally:
            if worker and worker.poll() is None:
                worker.terminate()
                worker.wait(timeout=40)


if __name__ == "__main__":
    main()
