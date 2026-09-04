"""Maintain the compact versioned inputs. Runtime never imports this generator or ground truth."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1] / "data/synthetic"
BASE = datetime(2026, 1, 15, 8, tzinfo=timezone.utc)
PLATE = "ZZ01AA0001"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


cameras = [
    {
        "id": f"C{i}",
        "zone_id": f"Z{(i + 1) // 2}",
        "name": f"Fictional camera {i}",
        "x": x,
        "y": y,
        "direction": "forward",
    }
    for i, (x, y) in enumerate(
        [(40, 100), (150, 100), (270, 40), (270, 160), (390, 100), (500, 100)], 1
    )
]
write(ROOT / "cameras.json", cameras)
edges = [
    {
        "source": a,
        "target": b,
        "distance_m": 1000,
        "min_seconds": 30,
        "max_seconds": 600,
        "baseline_seconds": 60,
    }
    for a, b in [("C1", "C2"), ("C2", "C3"), ("C2", "C4"), ("C3", "C5"), ("C4", "C5"), ("C5", "C6")]
]
write(ROOT / "graph.json", edges)


def event(scenario, kind, camera, seconds, passage, readings=None):
    return {
        "schema_version": "1",
        "event_id": str(
            uuid5(NAMESPACE_URL, f"roadeye/v1/{scenario}/{kind}/{camera}/{passage}/{seconds}")
        ),
        "kind": kind,
        "camera_id": camera,
        "lane_id": camera + "-L1",
        "captured_at": (BASE + timedelta(seconds=seconds)).isoformat(),
        "passage_id": passage,
        "readings": readings or [],
        "input_confidence": 1,
        "quality": 1,
        "evidence_key": "plate-card.svg",
        "source_mode": "synthetic",
        "inference_origin": "mock_candidates",
        "dataset_version": "1",
    }


def pair(scenario, camera, seconds, passage, plate=PLATE, readings=None):
    if readings is None:
        readings = [
            {"frame_id": passage + "-frame1", "candidates": [{"text": plate, "confidence": 0.95}]}
        ]
    return [
        event(scenario, "passage", camera, seconds, passage),
        event(scenario, "ocr", camera, seconds, passage, readings),
    ]


scenarios = {}
for name in [
    "normal_journey",
    "watchlist_match",
    "duplicate_delivery",
    "late_arrival",
    "worker_recovery",
]:
    rows = pair(name, "C1", 0, "p1") + pair(name, "C2", 60, "p2") + pair(name, "C3", 120, "p3")
    if name == "watchlist_match":
        rows = pair(name, "C1", 0, "p1")
    if name == "late_arrival":
        rows = rows[:2] + rows[4:] + rows[2:4]
    if name == "duplicate_delivery":
        rows = rows + rows
    scenarios[name] = rows
scenarios["ocr_disagreement"] = pair(
    "ocr_disagreement",
    "C2",
    0,
    "p1",
    readings=[
        {
            "frame_id": "f1",
            "candidates": [
                {"text": PLATE, "confidence": 0.9},
                {"text": "ZZ01AA000I", "confidence": 0.85},
            ],
        },
        {"frame_id": "f1", "candidates": [{"text": PLATE, "confidence": 0.9}]},
        {"frame_id": "f2", "candidates": [{"text": "ZZ01AA0002", "confidence": 0.9}]},
    ],
)
scenarios["unreadable_plate"] = pair("unreadable_plate", "C1", 0, "p1", plate="????")
scenarios["impossible_travel"] = pair("impossible_travel", "C1", 0, "p1") + pair(
    "impossible_travel", "C6", 5, "p2"
)
scenarios["ambiguous_branch"] = (
    pair("ambiguous_branch", "C2", 0, "p1")
    + pair("ambiguous_branch", "C3", 60, "p2")
    + pair("ambiguous_branch", "C4", 65, "p3")
)
scenarios["plate_collision"] = pair("plate_collision", "C1", 0, "p1") + pair(
    "plate_collision", "C6", 0, "p2"
)
scenarios["camera_outage"] = pair("camera_outage", "C1", 180, "p1")
scenarios["congestion_proxy"] = []
for i, travel in enumerate([60, 60, 180, 180]):
    plate = f"ZZ01BB{i:04d}"
    scenarios["congestion_proxy"] += pair("congestion_proxy", "C1", i * 300, f"a{i}", plate) + pair(
        "congestion_proxy", "C2", i * 300 + travel, f"b{i}", plate
    )

expected = {
    "normal_journey": [3, 3, 0, 0],
    "ocr_disagreement": [1, 0, 1, 0],
    "unreadable_plate": [1, 0, 0, 1],
    "impossible_travel": [2, 2, 0, 0],
    "ambiguous_branch": [3, 3, 0, 0],
    "watchlist_match": [1, 1, 0, 0],
    "duplicate_delivery": [3, 3, 0, 0],
    "late_arrival": [3, 3, 0, 0],
    "camera_outage": [1, 1, 0, 0],
    "congestion_proxy": [8, 8, 0, 0],
    "plate_collision": [2, 2, 0, 0],
    "worker_recovery": [3, 3, 0, 0],
}
for name, rows in scenarios.items():
    end = max(datetime.fromisoformat(e["captured_at"]) for e in rows)
    seconds = int((end - BASE).total_seconds())
    # Initial and final explicit heartbeats, not inferred from traffic.
    rows = [event(name, "heartbeat", f"C{i}", 0, "initial") for i in range(1, 7)] + rows
    rows += [
        event(name, "heartbeat", f"C{i}", seconds, "final")
        for i in range(1, 7)
        if not (name == "camera_outage" and i == 6)
    ]
    write(ROOT / "scenarios" / f"{name}.json", rows)
    write(
        ROOT / "ground_truth" / f"{name}.json",
        dict(zip(["passages", "accepted", "review_required", "rejected"], expected[name])),
    )
(ROOT / "evidence/plate-card.svg").write_text(
    """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="220" viewBox="0 0 640 220"><rect width="640" height="220" fill="#f5f4ef"/><rect x="20" y="20" width="600" height="180" fill="white" stroke="#334155"/><text x="320" y="90" text-anchor="middle" font-family="sans-serif" font-size="30">SYNTHETIC EVIDENCE</text><text x="320" y="140" text-anchor="middle" font-family="sans-serif" font-size="18">Fictional passage illustration — no OCR performed</text><text x="320" y="175" text-anchor="middle" font-family="sans-serif" font-size="16">Candidates are supplied separately by the mock adapter</text></svg>\n"""
)
files = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(ROOT.rglob("*"))
    if p.is_file() and p.name != "manifest.json"
}
write(
    ROOT / "manifest.json",
    {
        "dataset_version": "1",
        "schema_version": "1",
        "seed": 172,
        "source_mode": "synthetic",
        "inference_origin": "mock_candidates",
        "event_time_start": BASE.isoformat(),
        "event_time_end": (BASE + timedelta(seconds=1081)).isoformat(),
        "coordinate_system": "fictional local schematic units; not geographic installations",
        "scenarios": {
            n: {
                "purpose": n.replace("_", " "),
                "expected_coverage": "six explicit heartbeat sources; C6 deliberately stale in outage",
            }
            for n in scenarios
        },
        "files": files,
        "limitations": "Invented identifiers, no real vehicle attribution, not training data, no recognition accuracy measurement",
    },
)
