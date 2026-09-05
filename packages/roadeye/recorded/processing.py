"""Leased video processing with deterministic replay and atomic durable input publication."""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5

import av
import cv2
from sqlalchemy import select

from roadeye import models as m
from roadeye import services as s
from roadeye.config import settings
from roadeye.contracts import Input
from roadeye.db import SessionLocal, now
from roadeye.evidence import digest
from roadeye.recorded.inference import Detector, Recognizer, Tracker, verify_models


class LeaseLost(RuntimeError):
    pass


def renew(db, job_id: str, token: str):
    job = db.scalar(select(m.Job).where(m.Job.id == job_id).with_for_update())
    if not job or job.state != "leased" or job.lease_token != token:
        raise LeaseLost("VIDEO_LEASE_LOST")
    job.lease_until = now() + timedelta(seconds=settings.lease_seconds)
    return job


def save_image(db, run_id: str, image, encoding: str = "jpg") -> m.Evidence:
    ok, encoded = cv2.imencode(
        "." + encoding, image, [cv2.IMWRITE_JPEG_QUALITY, 95] if encoding == "jpg" else []
    )
    if not ok:
        raise ValueError("EVIDENCE_ENCODE_FAILED")
    content = encoded.tobytes()
    fingerprint = digest(content)
    key = f"{run_id}/{fingerprint}.{encoding}"
    path = settings.recorded_evidence_root / key
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        with temporary.open("wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    if digest(path.read_bytes()) != fingerprint:
        raise ValueError("EVIDENCE_DIGEST_MISMATCH")
    asset = db.scalar(
        select(m.Evidence).where(m.Evidence.run_id == run_id, m.Evidence.object_key == key)
    )
    if not asset:
        asset = m.Evidence(
            run_id=run_id,
            object_key=key,
            digest=fingerprint,
            size=len(content),
            media_type="image/jpeg" if encoding == "jpg" else "image/png",
            source_mode="recorded_real",
        )
        db.add(asset)
        db.flush()
    return asset


def publish(job_id: str, token: str, run_id: str, config: dict, track: dict):
    if not track["crossed"]:
        return
    with SessionLocal.begin() as db:
        s.require_run(db, run_id, lock=True)
        renew(db, job_id, token)
        crossing = track["crossing"]
        original = save_image(db, run_id, track["crossing_image"])
        samples, readings = [], []
        for sample in sorted(track["samples"], key=lambda item: item["pts"]):
            crop = save_image(db, run_id, sample["crop"], config.get("crop_encoding", "jpg"))
            frame = save_image(db, run_id, sample["image"])
            samples.append(
                {k: v for k, v in sample.items() if k not in ("crop", "image", "rank")}
                | {"crop_evidence_id": crop.id, "frame_evidence_id": frame.id}
            )
            readings.append(
                {
                    "frame_id": f"pts:{sample['pts']}",
                    "candidates": [
                        {"text": sample["ocr"]["text"], "confidence": sample["ocr"]["confidence"]}
                    ],
                }
            )
        metadata = {
            "relative_seconds": crossing["seconds"],
            "pts": crossing["pts"],
            "anchor_meaning": config["anchor_meaning"],
            "model_policy": config["policy"],
            "vehicle_detection": crossing["vehicle"],
            "track_hits": track["hits"],
        }
        timestamp = datetime.fromisoformat(config["replay_anchor"]) + timedelta(
            seconds=crossing["seconds"]
        )
        for kind in ("passage", "ocr"):
            event_id = str(uuid5(UUID(run_id), f"{track['id']}:{kind}"))
            payload = {
                "run_id": run_id,
                "event_id": event_id,
                "kind": kind,
                "camera_id": "REAL_C1",
                "lane_id": "REAL_C1-L1",
                "passage_id": track["id"],
                "captured_at": timestamp.isoformat(),
                "evidence_key": original.object_key,
                "source_mode": "recorded_real",
                "inference_origin": "model_inference",
                "metadata": metadata
                | (
                    {
                        "samples": samples,
                        "plate_detected": bool(samples),
                        "reason": "PLATE_CROPS_INFERRED"
                        if samples
                        else "NO_USABLE_PLATE_DETECTION",
                    }
                    if kind == "ocr"
                    else {}
                ),
                "readings": readings if kind == "ocr" else [],
            }
            s.ingest(db, Input.model_validate(payload), "worker", f"recorded:{event_id}", job_id)
        s.audit(db, "worker", "recording.passage_published", track["id"], run_id)


def relative_time(frame, start_pts: int, time_base) -> float:
    if frame.pts is None:
        raise ValueError("FRAME_PTS_MISSING")
    return float((frame.pts - start_pts) * time_base)


def ocr_due(seconds: float, last: float, policy: str) -> bool:
    # Exact 600ms PTS intervals can subtract to 0.5999999999999999.
    # Keep old runs byte-for-byte replayable; v2 fixes only this numerical boundary.
    epsilon = 1e-9 if policy == "recorded-onnx-v2" else 0.0
    return seconds - last + epsilon >= 0.6


def process_video(job_id: str, token: str) -> bool:
    started = time.monotonic()
    with SessionLocal.begin() as db:
        renew(db, job_id, token)
        task = db.get(m.VideoTask, job_id)
        assert task
        config, run_id = task.config, task.run_id
        task.progress = {"stage": "loading_models", "frames_decoded": 0, "frames_processed": 0}
    if not settings.recorded_enabled:
        raise ValueError("RECORDED_MODE_DISABLED")
    if verify_models(settings.model_root) != config["models"]:
        raise ValueError("RUN_MODEL_MANIFEST_CHANGED")
    path = Path(config["manifest"]["path"])
    if digest(path.read_bytes()) != config["manifest"]["sha256"]:
        raise ValueError("RECORDING_DIGEST_MISMATCH")
    vehicle, plate, ocr = (
        Detector(settings.model_root, "vehicle"),
        Detector(settings.model_root, "plate"),
        Recognizer(settings.model_root),
    )
    tracker = Tracker(config["line_y"])
    decoded = processed = crossings = detected = 0
    next_sample = 0.0
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        start_pts = stream.start_time or 0
        for frame in container.decode(stream):
            seconds = relative_time(frame, start_pts, stream.time_base)
            if seconds >= config["duration_seconds"]:
                break
            decoded += 1
            if seconds + 1e-9 < next_sample:
                continue
            next_sample += 1 / config["sample_fps"]
            processed += 1
            image = frame.to_ndarray(format="bgr24")
            top = config["roi_top"]
            detections = vehicle.detect(image[top:])
            for detection in detections:
                detection["box"][1] += top
                detection["box"][3] += top
            assignments, expired = tracker.update(detections, seconds, frame.pts)
            for track, detection in assignments:
                if track["crossed"] and "crossing_image" not in track:
                    track["crossing_image"] = image.copy()
                x, y, x2, y2 = detection["box"]
                # Only useful nearby vehicle crops; expensive OCR at most every 0.6s/track.
                if (
                    y2 < 200
                    or x2 - x < 120
                    or not ocr_due(seconds, track.get("last_ocr", -10), config["policy"])
                ):
                    continue
                track["last_ocr"] = seconds
                vehicle_crop = image[max(top, y) : y2, x:x2]
                candidates = plate.detect(vehicle_crop)
                for candidate in sorted(candidates, key=lambda c: -c["score"])[:1]:
                    px, py, px2, py2 = candidate["box"]
                    px, px2, py, py2 = px + x, px2 + x, py + max(top, y), py2 + max(top, y)
                    if py < top or px2 - px < 24 or py2 - py < 10:
                        continue
                    crop = image[py:py2, px:px2].copy()
                    sample = {
                        "pts": frame.pts,
                        "relative_seconds": seconds,
                        "plate_box": [px, py, px2, py2],
                        "plate_score": candidate["score"],
                        "ocr": ocr.recognize(crop),
                        "crop": crop,
                        "image": image.copy(),
                        "rank": (px2 - px) * (py2 - py) * candidate["score"],
                    }
                    if config["policy"] == "recorded-onnx-v2":
                        sample["vehicle_box"] = detection["box"]
                    track["samples"].append(sample)
                    track["samples"] = sorted(
                        track["samples"], key=lambda a: (-a["rank"], a["pts"])
                    )[:3]
            for track in expired:
                if track["crossed"]:
                    publish(job_id, token, run_id, config, track)
                    crossings += 1
                    detected += bool(track["samples"])
            with SessionLocal.begin() as db:
                renew(db, job_id, token)
                task = db.get(m.VideoTask, job_id)
                assert task
                task.progress = {
                    "stage": "inference",
                    "frames_decoded": decoded,
                    "frames_processed": processed,
                    "relative_seconds": seconds,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "published_passages": crossings,
                    "passages_with_plate_detections": detected,
                }
    for track in tracker.tracks.values():
        if track["crossed"]:
            publish(job_id, token, run_id, config, track)
            crossings += 1
            detected += bool(track["samples"])
    with SessionLocal.begin() as db:
        run = s.require_run(db, run_id, lock=True)
        job = renew(db, job_id, token)
        job.state, job.processed_at, job.lease_until, job.error = "done", now(), None, None
        task = db.get(m.VideoTask, job_id)
        assert task
        task.progress = {
            "stage": "inference_completed",
            "frames_decoded": decoded,
            "frames_processed": processed,
            "relative_seconds": config["duration_seconds"],
            "duration_seconds": round(time.monotonic() - started, 3),
            "published_passages": crossings,
            "passages_with_plate_detections": detected,
            "hardware": "CPUExecutionProvider; 2 ONNX intra-op threads",
            "missing_evidence": 0,
        }
        run.state = "delivered"
        run.clock = datetime.fromisoformat(config["replay_anchor"]) + timedelta(
            seconds=config["duration_seconds"]
        )
        s.audit(
            db, "worker", "recording.inference_completed", job_id, run_id, details=task.progress
        )
    return True
