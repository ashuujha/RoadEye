"""Build a private, label-bearing S01/S03 crop bundle for the Colab job."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

from roadeye.phase2 import ROOT
from roadeye.reid_training import identity_split
from roadeye.tracklets import sha256, write_json

LOGGER = logging.getLogger("roadeye.build_reid_training_bundle")


def spaced(rows: list[dict], count: int) -> list[dict]:
    if len(rows) <= count:
        return rows
    indexes = [round(index * (len(rows) - 1) / (count - 1)) for index in range(count)]
    if len(set(indexes)) != count:
        raise ValueError("Could not select unique spaced observations")
    return [rows[index] for index in indexes]


def collect(config: dict, dataset: Path) -> tuple[dict, dict, dict]:
    if config["partition"] != "train" or set(config["scenarios"]) != {"S01", "S03"}:
        raise ValueError("Training bundle is restricted to train/S01 and train/S03")
    if set(config["scenarios"]) & set(config["allowed_evaluation_scenarios"]):
        raise ValueError("Training and evaluation scenarios overlap")
    visits: dict[tuple[str, str], list[dict]] = defaultdict(list)
    identities: dict[str, list[str]] = defaultdict(list)
    sources = {}
    for scenario in config["scenarios"]:
        offsets_path = dataset / "cam_timestamp" / f"{scenario}.txt"
        offsets = dict(line.split() for line in offsets_path.read_text().splitlines())
        sources[offsets_path.relative_to(dataset).as_posix()] = sha256(offsets_path)
        for camera_path in sorted(
            (dataset / config["partition"] / scenario).glob("c*")
        ):
            camera = camera_path.name
            gt_path, video_path = camera_path / "gt/gt.txt", camera_path / "vdo.avi"
            if (
                camera not in offsets
                or not gt_path.is_file()
                or not video_path.is_file()
            ):
                raise FileNotFoundError(
                    f"Incomplete training camera: {scenario}/{camera}"
                )
            fps = 8 if scenario == "S03" and camera == "c015" else 10
            with gt_path.open(newline="", encoding="utf-8") as stream:
                for line_number, row in enumerate(csv.reader(stream), 1):
                    if len(row) < 6:
                        raise ValueError(f"Malformed GT row: {gt_path}:{line_number}")
                    frame, source_identity = int(row[0]), row[1]
                    box = [float(value) for value in row[2:6]]
                    if not np.isfinite(box).all() or min(box[2:]) <= 0:
                        raise ValueError(f"Invalid GT box: {gt_path}:{line_number}")
                    identity = f"train/{scenario}/{source_identity}"
                    visits[(identity, camera)].append(
                        {
                            "identity": identity,
                            "scenario": scenario,
                            "camera": camera,
                            "frame": frame,
                            "time_s": float(offsets[camera]) + (frame - 1) / fps,
                            "bbox_xywh": box,
                            "gt_source_line": line_number,
                        }
                    )
                    identities[scenario].append(identity)
            sources[gt_path.relative_to(dataset).as_posix()] = sha256(gt_path)
            sources[video_path.relative_to(dataset).as_posix()] = sha256(video_path)
    for rows in visits.values():
        rows.sort(key=lambda row: row["frame"])
    return visits, identities, sources


def build(config_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite training bundle: {output}")
    config = json.loads(config_path.read_text())
    dataset = ROOT / config["dataset_root"]
    visits, identities, sources = collect(config, dataset)
    split = identity_split(
        identities,
        config["split"]["development_fraction_per_scenario"],
        config["split"]["seed"],
    )
    selected: dict[tuple[str, str], list[dict]] = {}
    count = config["crop_export"]["samples_per_identity_camera"]
    for key, rows in visits.items():
        selected[key] = spaced(rows, count)
    output.mkdir(parents=True)
    records, exclusions = [], []
    by_camera: dict[tuple[str, str], dict[int, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for rows in selected.values():
        for row in rows:
            by_camera[(row["scenario"], row["camera"])][row["frame"]].append(row)
    for (scenario, camera), wanted in sorted(by_camera.items()):
        video = dataset / config["partition"] / scenario / camera / "vdo.avi"
        capture = cv2.VideoCapture(str(video))
        try:
            if not capture.isOpened():
                raise RuntimeError(f"Cannot open {video}")
            expected_fps = 8 if scenario == "S03" and camera == "c015" else 10
            if abs(capture.get(cv2.CAP_PROP_FPS) - expected_fps) > 0.02:
                raise RuntimeError(f"Unexpected FPS: {scenario}/{camera}")
            for frame_number in range(1, max(wanted) + 1):
                if not capture.grab():
                    raise RuntimeError(
                        f"Video ended early: {scenario}/{camera}/{frame_number}"
                    )
                if frame_number not in wanted:
                    continue
                ok, image = capture.retrieve()
                if not ok:
                    raise RuntimeError(
                        f"Decode failed: {scenario}/{camera}/{frame_number}"
                    )
                height, width = image.shape[:2]
                for source in wanted[frame_number]:
                    x, y, box_width, box_height = source["bbox_xywh"]
                    left, top = max(0, math.floor(x)), max(0, math.floor(y))
                    right = min(width, math.ceil(x + box_width))
                    bottom = min(height, math.ceil(y + box_height))
                    if (
                        min(right - left, bottom - top)
                        < config["crop_export"]["min_clipped_side_px"]
                    ):
                        exclusions.append(
                            {**source, "reason": "clipped_crop_too_small"}
                        )
                        continue
                    identity_number = source["identity"].rsplit("/", 1)[1]
                    relative = (
                        Path("images")
                        / split[source["identity"]]
                        / (
                            f"{scenario}_{camera}_{identity_number}_{frame_number:06d}.jpg"
                        )
                    )
                    target = output / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not cv2.imwrite(
                        str(target),
                        image[top:bottom, left:right],
                        [
                            cv2.IMWRITE_JPEG_QUALITY,
                            config["crop_export"]["jpeg_quality"],
                        ],
                    ):
                        raise RuntimeError(f"Could not write {target}")
                    records.append(
                        {
                            **source,
                            "split": split[source["identity"]],
                            "image": relative.as_posix(),
                            "image_sha256": sha256(target),
                            "clipped_xyxy": [left, top, right, bottom],
                            "label_provenance": "released_CityFlow_GT_training_partition_only",
                        }
                    )
        finally:
            capture.release()
        LOGGER.info(
            "extracted scenario=%s camera=%s crops=%s",
            scenario,
            camera,
            sum(r["scenario"] == scenario and r["camera"] == camera for r in records),
        )
    records.sort(key=lambda row: row["image"])
    records_path = output / "records.jsonl"
    with records_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(
                json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n"
            )
    train_ids = {r["identity"] for r in records if r["split"] == "train"}
    development_ids = {r["identity"] for r in records if r["split"] == "development"}
    identity_cameras: dict[str, set[str]] = defaultdict(set)
    for record in records:
        identity_cameras[record["identity"]].add(record["camera"])
    invalid_identities = sorted(
        identity for identity, cameras in identity_cameras.items() if len(cameras) < 2
    )
    if invalid_identities:
        raise ValueError(
            f"Crop filtering removed cross-camera evidence for {invalid_identities}"
        )
    manifest = {
        "schema_version": 1,
        "purpose": config["purpose"],
        "license_handling": "private_training_artifact_do_not_commit_or_redistribute",
        "config_sha256": sha256(config_path),
        "records_sha256": sha256(records_path),
        "source_sha256": sources,
        "counts": {
            "records": len(records),
            "train_records": sum(r["split"] == "train" for r in records),
            "development_records": sum(r["split"] == "development" for r in records),
            "train_identities": len(train_ids),
            "development_identities": len(development_ids),
            "identity_overlap": len(train_ids & development_ids),
            "cameras": len({(r["scenario"], r["camera"]) for r in records}),
            "identities_with_two_or_more_cameras": sum(
                len(cameras) >= 2 for cameras in identity_cameras.values()
            ),
            "excluded_crops": len(exclusions),
        },
        "records_by_scenario_split": dict(
            Counter(f"{r['scenario']}/{r['split']}" for r in records)
        ),
        "identities_by_scenario_split": dict(
            Counter(
                f"{identity.split('/')[1]}/{split_name}"
                for identity, split_name in split.items()
            )
        ),
        "split": config["split"],
        "crop_export": config["crop_export"],
        "exclusions": exclusions,
    }
    if manifest["counts"]["identity_overlap"]:
        raise ValueError("Identity leakage detected")
    write_json(output / "manifest.json", manifest)
    archive = output.parent / "roadeye-reid-training-data.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        for path in sorted(p for p in output.rglob("*") if p.is_file()):
            bundle.write(path, path.relative_to(output))
    result = {
        "status": "PASS",
        "bundle": output.as_posix(),
        "bundle_manifest_sha256": sha256(output / "manifest.json"),
        "archive": archive.as_posix(),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha256(archive),
        **manifest["counts"],
    }
    write_json(output.parent / "bundle-build.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/reid-training.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/reid-training/data"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print(json.dumps(build(args.config, args.output), indent=2))


if __name__ == "__main__":
    main()
