"""Read predicted MTSC observations. This module never opens identity labels."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


@dataclass(frozen=True)
class Observation:
    key: str
    camera: str
    frame: int
    time_s: float
    bbox_xywh: tuple[float, float, float, float]
    baseline_score: float


@dataclass
class Tracklet:
    key: str
    partition: str
    scenario: str
    camera: str
    local_id: int
    observations: list[Observation]


def checked_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes dataset root: {relative}")
    return path


def load_tracklets(root: Path, window: dict) -> tuple[list[Tracklet], dict]:
    """Preserve every baseline track in the manifest window; no camera-order cap."""
    if window["start_s"] > window["end_s"]:
        raise ValueError("Invalid window")
    result: list[Tracklet] = []
    sources: dict = {}
    cameras = set()
    for camera in window["cameras"]:
        cam = camera["camera_id"]
        if cam in cameras:
            raise ValueError(f"Duplicate camera {cam}")
        cameras.add(cam)
        path = checked_path(root, camera["baseline_tracks"])
        if path.parent.name != "mtsc" or not path.name.startswith("mtsc_"):
            raise ValueError("Runtime accepts predicted MTSC inputs only")
        digest = sha256(path)
        if digest != camera["baseline_sha256"]:
            raise ValueError(f"Baseline hash mismatch: {cam}")
        sources[cam] = {"baseline_sha256": digest}
        groups: dict[int, list[Observation]] = {}
        seen = set()
        fps = camera["fps_from_readme"]
        if fps <= 0:
            raise ValueError("Invalid FPS")
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                if not row:
                    continue
                if len(row) != 10:
                    raise ValueError(f"Malformed MOT row in {path}")
                frame, local_id = int(row[0]), int(row[1])
                box = tuple(float(x) for x in row[2:6])
                score = float(row[6])
                if not np.isfinite((*box, score)).all() or min(box[2:]) <= 0:
                    raise ValueError(f"Invalid box in {path}")
                if not 1 <= frame <= camera["declared_frames"]:
                    raise ValueError(f"Frame outside declared video: {cam}/{frame}")
                timestamp = camera["offset_s"] + (frame - 1) / fps
                if not window["start_s"] <= timestamp <= window["end_s"]:
                    continue
                if (local_id, frame) in seen:
                    raise ValueError(
                        f"Duplicate local track/frame: {cam}/{local_id}/{frame}"
                    )
                seen.add((local_id, frame))
                key = f"{window['partition']}/{window['scenario']}/{cam}/{local_id}"
                groups.setdefault(local_id, []).append(
                    Observation(key, cam, frame, timestamp, box, score)
                )
        for local_id, rows in sorted(groups.items()):
            rows.sort(key=lambda r: r.frame)
            result.append(
                Tracklet(
                    rows[0].key,
                    window["partition"],
                    window["scenario"],
                    cam,
                    local_id,
                    rows,
                )
            )
    if not result:
        raise ValueError("No baseline observations in the selected window")
    return result, sources


def camera_positions(root: Path, window: dict) -> dict:
    """Calibration-derived road-plane reference points, NOT surveyed camera GPS."""
    positions = {}
    for camera in window["cameras"]:
        calibration = checked_path(root, camera["calibration"])
        video = checked_path(root, camera["video"])
        if video.stat().st_size != camera["video_bytes"]:
            raise ValueError(f"Video size mismatch: {video}")
        lines = calibration.read_text(encoding="utf-8").splitlines()
        matrix = np.array(
            [
                [float(v) for v in row.split()]
                for row in lines[0].split(":", 1)[1].split(";")
            ]
        )
        roi_path = video.parent / "roi.jpg"
        roi = cv2.imread(str(roi_path), cv2.IMREAD_GRAYSCALE)
        if roi is None:
            raise ValueError(f"Unreadable ROI: {roi_path}")
        ys, xs = np.where(roi > 127)
        if not len(xs):
            raise ValueError(f"Empty ROI: {roi_path}")
        point = np.linalg.solve(
            matrix, [float(np.median(xs)), float(np.median(ys)), 1.0]
        )
        lat, lon = (point[:2] / point[2]).tolist()
        if (
            not np.isfinite([lat, lon]).all()
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
        ):
            raise ValueError(f"Invalid calibration reference: {camera['camera_id']}")
        positions[camera["camera_id"]] = {
            "latitude": lat,
            "longitude": lon,
            "kind": "inverse_homography_roi_median_road_reference_not_camera_GPS",
            "calibration_sha256": sha256(calibration),
            "roi_sha256": sha256(roi_path),
        }
    return positions


def extract_crops(
    root: Path, window: dict, tracklets: list[Tracklet], output: Path, sample_count: int
) -> tuple[dict, list[dict]]:
    """One sequential video pass per camera, using the first K observations only."""
    samples: dict[str, list[dict]] = {}
    failures = []
    for camera in window["cameras"]:
        cam = camera["camera_id"]
        wanted: dict[int, list[Observation]] = {}
        tracks = [t for t in tracklets if t.camera == cam]
        for track in tracks:
            if len(track.observations) < sample_count:
                failures.append(
                    {"key": track.key, "reason": "fewer_than_prefix_sample_count"}
                )
                continue
            for observation in track.observations[:sample_count]:
                wanted.setdefault(observation.frame, []).append(observation)
        if not wanted:
            continue
        cap = cv2.VideoCapture(str(checked_path(root, camera["video"])))
        try:
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open {cam} video")
            actual_fps = cap.get(cv2.CAP_PROP_FPS)
            if abs(actual_fps - camera["fps_from_readme"]) > 0.02:
                raise RuntimeError(f"FPS mismatch for {cam}: {actual_fps}")
            for frame_number in range(1, max(wanted) + 1):
                if not cap.grab():
                    raise RuntimeError(f"Video ended early: {cam}/{frame_number}")
                if frame_number not in wanted:
                    continue
                ok, image = cap.retrieve()
                if not ok:
                    raise RuntimeError(f"Decode failed: {cam}/{frame_number}")
                height, width = image.shape[:2]
                for observation in wanted[frame_number]:
                    x, y, w, h = observation.bbox_xywh
                    left, top = max(0, int(np.floor(x))), max(0, int(np.floor(y)))
                    right, bottom = (
                        min(width, int(np.ceil(x + w))),
                        min(height, int(np.ceil(y + h))),
                    )
                    if right - left < 2 or bottom - top < 2:
                        failures.append(
                            {
                                "key": observation.key,
                                "reason": "empty_clipped_crop",
                                "frame": frame_number,
                            }
                        )
                        continue
                    relative = (
                        Path("crops") / observation.key / f"{frame_number:06d}.jpg"
                    )
                    path = output / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not cv2.imwrite(str(path), image[top:bottom, left:right]):
                        raise RuntimeError(f"Could not save {path}")
                    samples.setdefault(observation.key, []).append(
                        {
                            **asdict(observation),
                            "video": camera["video"],
                            "crop": relative.as_posix(),
                            "crop_sha256": sha256(path),
                            "clipped_xyxy": [left, top, right, bottom],
                            "score_kind": "baseline_track_score_not_calibrated_detection_confidence",
                        }
                    )
        finally:
            cap.release()
        print(
            f"Crops {cam}: {sum(t.key in samples for t in tracks)}/{len(tracks)} tracklets",
            flush=True,
        )
    for key in list(samples):
        if len(samples[key]) != sample_count:
            failures.append({"key": key, "reason": "incomplete_prefix_crops"})
            del samples[key]
    return samples, failures
