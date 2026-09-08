"""Freeze clock-selected comparison windows using metadata only, never GT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from roadeye.phase2 import ROOT
from roadeye.tracklets import sha256, write_json


def freeze_window(dataset: Path, spec: dict, output: Path) -> None:
    scenario = spec["scenario"]
    offsets_path = dataset / "cam_timestamp" / f"{scenario}.txt"
    frames_path = dataset / "cam_framenum" / f"{scenario}.txt"
    offsets = dict(line.split() for line in offsets_path.read_text().splitlines())
    frames = dict(line.split() for line in frames_path.read_text().splitlines())
    cameras = []
    for camera in sorted((dataset / spec["partition"] / scenario).iterdir()):
        if not camera.is_dir() or camera.name not in offsets:
            continue
        video = camera / "vdo.avi"
        baseline = camera / "mtsc/mtsc_deepsort_mask_rcnn.txt"
        cameras.append(
            {
                "camera_id": camera.name,
                "video": video.relative_to(dataset.parent).as_posix(),
                "video_bytes": video.stat().st_size,
                "offset_s": float(offsets[camera.name]),
                "fps_from_readme": 8
                if scenario == "S03" and camera.name == "c015"
                else 10,
                "declared_frames": int(frames[camera.name]),
                "calibration": (camera / "calibration.txt")
                .relative_to(dataset.parent)
                .as_posix(),
                "baseline_tracks": baseline.relative_to(dataset.parent).as_posix(),
                "baseline_sha256": sha256(baseline),
            }
        )
    if set(offsets) != {c["camera_id"] for c in cameras}:
        raise ValueError("Missing scenario cameras; do not silently shrink the window")
    manifest = {
        "schema_version": 1,
        "dataset": "CityFlow-V2_AIC22_Track1",
        **spec,
        "interval": "closed",
        "time_basis": "scenario_relative_seconds",
        "frame_time_rule": "offset_s + (one_based_frame - 1) / fps",
        "selection_rule": "first_180_seconds_all_cameras_without_identity_annotations",
        "cameras": cameras,
        "metadata_sha256": {
            "timestamps": sha256(offsets_path),
            "frame_counts": sha256(frames_path),
            "readme": sha256(dataset / "ReadMe.txt"),
        },
    }
    if output.exists() and json.loads(output.read_text()) != manifest:
        raise ValueError("Frozen window differs; refusing to overwrite")
    write_json(output, manifest)
    print(
        f"{output.name}: {len(cameras)} cameras, {spec['start_s']} to {spec['end_s']} s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "configs/reid-experiment.json",
    )
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    dataset = ROOT / "data/cityflow/AICity22_Track1_MTMC_Tracking"
    for role in ("development", "evaluation"):
        if role not in protocol:
            continue
        output = protocol.get("window_outputs", {}).get(
            role, f"configs/reid-{role}-window.json"
        )
        freeze_window(
            dataset,
            protocol[role],
            ROOT / output,
        )


if __name__ == "__main__":
    main()
