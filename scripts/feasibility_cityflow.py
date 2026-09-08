"""Inspect released CityFlow files; no detection, embeddings, or association."""

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "cityflow"
DATA = DATA_ROOT / "AICity22_Track1_MTMC_Tracking"
OUT = ROOT / "reports" / "private"
OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "configs").mkdir(exist_ok=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(DATA_ROOT).as_posix()


offsets = {}
frame_counts = {}
for path in sorted((DATA / "cam_timestamp").glob("*.txt")):
    offsets[path.stem] = {r[0]: float(r[1]) for r in map(str.split, path.read_text().splitlines()) if r}
for path in sorted((DATA / "cam_framenum").glob("*.txt")):
    frame_counts[path.stem] = {r[0]: int(r[1]) for r in map(str.split, path.read_text().splitlines()) if r}

inventory = []
identities = defaultdict(lambda: defaultdict(list))
scenario_stats = {}
bad_rows = []
gt_row_count = 0
for partition in ("train", "validation", "test"):
    for scenario in sorted((DATA / partition).glob("S*")):
        for camera in sorted(scenario.glob("c*")):
            gt = camera / "gt" / "gt.txt"
            fps = 8 if scenario.name == "S03" and camera.name == "c015" else 10
            record = {
                "partition": partition, "scenario": scenario.name, "camera": camera.name,
                "video": rel(camera / "vdo.avi"),
                "video_bytes": (camera / "vdo.avi").stat().st_size if (camera / "vdo.avi").exists() else None,
                "calibration": rel(camera / "calibration.txt"),
                "calibration_exists": (camera / "calibration.txt").exists(),
                "roi_exists": (camera / "roi.jpg").exists(),
                "baseline_files": [rel(p) for p in sorted((camera / "mtsc").glob("*.txt"))],
                "detection_files": [rel(p) for p in sorted((camera / "det").glob("*.txt"))],
                "gt_file": rel(gt) if gt.exists() else None,
                "offset_s": offsets[scenario.name][camera.name], "fps_from_readme": fps,
                "declared_frames": frame_counts[scenario.name][camera.name],
            }
            if gt.exists():
                record["gt_sha256"] = sha256(gt)
                for line_number, row in enumerate(csv.reader(gt.read_text().splitlines()), 1):
                    if not row:
                        continue
                    if len(row) != 10:
                        bad_rows.append([rel(gt), line_number, "column_count"])
                        continue
                    frame, identity = int(row[0]), int(row[1])
                    box = list(map(float, row[2:6]))
                    if not 1 <= frame <= record["declared_frames"] or min(box[2:]) <= 0:
                        bad_rows.append([rel(gt), line_number, "frame_or_box"])
                    identities[(partition, scenario.name, identity)][camera.name].append(
                        {"frame": frame, "bbox_xywh": box, "timestamp_s": record["offset_s"] + (frame - 1) / fps}
                    )
                    gt_row_count += 1
            inventory.append(record)

coverage = []
for (partition, scenario, identity), cameras in identities.items():
    first = min(v["timestamp_s"] for rows in cameras.values() for v in rows)
    last = max(v["timestamp_s"] for rows in cameras.values() for v in rows)
    coverage.append({"partition": partition, "scenario": scenario, "identity": identity,
                     "camera_count": len(cameras), "cameras": sorted(cameras),
                     "first_s": first, "last_s": last, "span_s": last - first,
                     "row_count": sum(map(len, cameras.values()))})
coverage.sort(key=lambda r: (-r["camera_count"], r["span_s"], r["scenario"], r["identity"]))
for scenario in sorted(offsets):
    rows = [r for r in coverage if r["scenario"] == scenario]
    cams = [r for r in inventory if r["scenario"] == scenario]
    scenario_stats[scenario] = {
        "partition": cams[0]["partition"], "camera_instances": len(cams),
        "released_identities": len(rows), "gt_rows": sum(r["row_count"] for r in rows),
        "max_cameras_per_released_identity": max((r["camera_count"] for r in rows), default=None),
        "identities_at_least_six_cameras": sum(r["camera_count"] >= 6 for r in rows),
    }
with (OUT / "cityflow-identity-coverage.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(coverage[0]))
    writer.writeheader()
    writer.writerows(coverage)

best = coverage[0]
evidence = []
if best["camera_count"] >= 6:
    chosen_cameras = identities[(best["partition"], best["scenario"], best["identity"])]
    camera_records = []
    # Include every camera in the scenario that has footage overlapping the selected interval.
    # Selection uses GT only during feasibility; the runtime window contains no target identity.
    for camera in [r for r in inventory if r["scenario"] == best["scenario"]]:
        video_end = camera["offset_s"] + (camera["declared_frames"] - 1) / camera["fps_from_readme"]
        if video_end < best["first_s"] or camera["offset_s"] > best["last_s"]:
            continue
        baseline = next((p for p in camera["baseline_files"] if p.endswith("mtsc_deepsort_mask_rcnn.txt")), None)
        camera_records.append({
            "camera_id": camera["camera"], "video": camera["video"], "video_bytes": camera["video_bytes"],
            "offset_s": camera["offset_s"], "fps_from_readme": camera["fps_from_readme"],
            "declared_frames": camera["declared_frames"], "calibration": camera["calibration"],
            "baseline_tracks": baseline,
            "baseline_sha256": sha256(DATA_ROOT / baseline) if baseline else None,
        })
    for camera, rows in sorted(chosen_cameras.items()):
        rows.sort(key=lambda r: r["frame"])
        middle = rows[len(rows) // 2]
        evidence.append({"camera": camera, "first_frame": rows[0]["frame"], "last_frame": rows[-1]["frame"],
                         "first_s": rows[0]["timestamp_s"], "last_s": rows[-1]["timestamp_s"],
                         "rows": len(rows), "inspection_frame": middle})
    window = {
        "schema_version": 1, "purpose": "feasibility_selection_only_not_model_predictions",
        "dataset": "CityFlow-V2_AIC22_Track1", "partition": best["partition"], "scenario": best["scenario"],
        "time_basis": "scenario_relative_seconds", "frame_time_rule": "offset_s + (one_based_frame - 1) / fps",
        "start_s": best["first_s"], "end_s": best["last_s"], "interval": "closed",
        "selection_rule": "shortest full first-to-last span among identities with maximum released camera coverage",
        "candidate_policy": "all baseline observations within this interval in every overlapping scenario camera",
        "cameras": camera_records,
        "readme_sha256": sha256(DATA / "ReadMe.txt"),
        "timestamp_sha256": sha256(DATA / "cam_timestamp" / (best["scenario"] + ".txt")),
    }
    (ROOT / "configs" / "feasibility-window.json").write_text(json.dumps(window, indent=2) + "\n", encoding="utf-8")

summary = {
    "source": "user supplied extracted dataset; original archive checksum unavailable",
    "camera_instances": len(inventory), "distinct_camera_ids": len({r["camera"] for r in inventory}),
    "video_bytes": sum(r["video_bytes"] or 0 for r in inventory),
    "gt_files": sum(r["gt_file"] is not None for r in inventory), "gt_rows": gt_row_count,
    "identities_scoped_to_scenario": len(coverage), "bad_gt_rows": bad_rows,
    "scenarios": scenario_stats, "best_released_identity": best, "best_identity_evidence": evidence,
    "coverage_scope": "all uploaded train and validation per-camera labels; hidden test labels not available",
    "inventory": inventory,
}
(OUT / "cityflow-audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k not in ("inventory", "best_identity_evidence")}, indent=2))
print("Selected evidence:", json.dumps(evidence, indent=2))
