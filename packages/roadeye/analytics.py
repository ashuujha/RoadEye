from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from roadeye import models as m
from roadeye.contracts import TrajectoryQuery, Window
from roadeye.services import health, observation_rows, require_run, trajectory


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * p
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def summary(db: Session, window: Window) -> dict:
    run = require_run(db, str(window.run_id), lock=True)
    passages = db.execute(
        select(m.Passage.camera_id, m.Passage.lane_id, func.count())
        .where(
            m.Passage.run_id == run.id,
            m.Passage.captured_at >= window.start,
            m.Passage.captured_at < window.end,
        )
        .group_by(m.Passage.camera_id, m.Passage.lane_id)
    ).all()
    observations = observation_rows(db, run.id, window.start, window.end)
    accepted = sum(o["status"] == "accepted" for o in observations)
    total = sum(p[2] for p in passages)
    camera_health = health(db, run)
    heartbeat_inputs = db.scalars(
        select(m.InputEvent)
        .join(m.Job, m.Job.id == m.InputEvent.id)
        .where(m.InputEvent.run_id == run.id, m.Job.state == "done")
    ).all()
    for camera_status in camera_health:
        intervals = []
        for event in heartbeat_inputs:
            payload = event.payload
            if payload["kind"] != "heartbeat" or payload["camera_id"] != camera_status["camera_id"]:
                continue
            captured = datetime.fromisoformat(payload["captured_at"])
            left, right = (
                max(window.start, captured),
                min(window.end, captured + timedelta(seconds=120)),
            )
            if left < right:
                intervals.append((left, right))
        covered = 0.0
        covered_until = window.start
        for left, right in sorted(intervals):
            covered += max(0.0, (right - max(left, covered_until)).total_seconds())
            covered_until = max(covered_until, right)
        camera_status["heartbeat_covered_seconds"] = covered
        camera_status["heartbeat_coverage_fraction"] = (
            covered / (window.end - window.start).total_seconds()
        )
        camera_status["coverage_meaning"] = (
            "Union of 120-second heartbeat validity intervals, not measured physical uptime"
        )
    counts = []
    for camera in db.scalars(
        select(m.Camera).where(m.Camera.id != "REAL_C1").order_by(m.Camera.id)
    ):
        number = next((n for c, lane, n in passages if c == camera.id), 0)
        recognized = sum(
            o["camera_id"] == camera.id and o["status"] == "accepted" for o in observations
        )
        state = next(h["state"] for h in camera_health if h["camera_id"] == camera.id)
        counts.append(
            {
                "camera_id": camera.id,
                "lane_id": camera.id + "-L1",
                "passages": number,
                "accepted_plates": recognized,
                "recognition_coverage": recognized / number if number else None,
                "count_rate_per_minute": number * 60 / (window.end - window.start).total_seconds(),
                "coverage_state": state,
            }
        )
    segments: dict[tuple[str, str], list[dict]] = defaultdict(list)
    od: dict[tuple[str, str], int] = defaultdict(int)
    excluded = 0
    plates = sorted({o["plate"] for o in observations if o["plate"] and o["status"] == "accepted"})
    for plate in plates:
        result = trajectory(
            db, TrajectoryQuery(**window.model_dump(), plate=plate, limit=200), save=False
        )
        if result["truncated"]:
            excluded += 1
            continue
        links = [link for link in result["inferred_links"] if link["status"] == "plausible"]
        excluded += sum(link["status"] == "ambiguous" for link in result["inferred_links"])
        for link in links:
            # Only directly adjacent camera pairs become segment statistics.
            if len(link["routes"][0]["cameras"]) == 2:
                segments[(link["source"], link["target"])].append(link)
        # Maximal unambiguous connected chains within the query window are enrolled-camera sessions.
        targets = {link["to"] for link in links}
        by_from = {link["from"]: link for link in links}
        for link in links:
            if link["from"] in targets:
                continue
            last = link
            visited = set()
            while last["to"] in by_from and last["to"] not in visited:
                visited.add(last["to"])
                last = by_from[last["to"]]
            od[(link["source"], last["target"])] += 1
    travel = []
    for (source, target), links in sorted(segments.items()):
        values = [link["elapsed_seconds"] for link in links]
        median = percentile(values, 0.5)
        baseline = links[0]["routes"][0]["baseline_seconds"]
        travel.append(
            {
                "source": source,
                "target": target,
                "sample_size": len(values),
                "median_seconds": median,
                "p90_seconds": percentile(values, 0.9),
                "segment_average_speed_kmh": percentile(
                    [
                        link["routes"][0]["distance_m"] / link["elapsed_seconds"] * 3.6
                        for link in links
                    ],
                    0.5,
                ),
                "synthetic_baseline_seconds": baseline,
                "congestion_proxy_ratio": median / baseline if median is not None else None,
            }
        )
    pending = db.scalar(
        select(func.count()).select_from(m.Job).where(m.Job.run_id == run.id, m.Job.state != "done")
    )
    return {
        "run_id": run.id,
        "source_mode": run.source_mode,
        "window_start": window.start.isoformat(),
        "window_end": window.end.isoformat(),
        "basis": "capture_time UTC [start,end)",
        "result_version": run.version,
        "status": "provisional" if pending else "current_recomputable",
        "sample_size": total,
        "vehicle_passages": total,
        "accepted_plates": accepted,
        "recognition_coverage": accepted / total if total else None,
        "review_required": sum(o["status"] == "review_required" for o in observations),
        "rejected": sum(o["status"] == "rejected" for o in observations),
        "ocr_pending": total - len(observations),
        "counts": counts,
        "camera_health": camera_health,
        "flow": [
            {"source": a, "target": b, "count": len(ls)} for (a, b), ls in sorted(segments.items())
        ],
        "od": [
            {"enrolled_origin": a, "enrolled_destination": b, "sessions": n}
            for (a, b), n in sorted(od.items())
        ],
        "travel_times": travel,
        "ambiguous_links_excluded": excluded,
        "limitations": [
            "Heartbeats show freshness at run clock, not measured uptime over the window.",
            "Missing coverage is not zero traffic; counts are observed only.",
            "OD uses maximal unambiguous enrolled-camera chains in this window, not true trip endpoints.",
            "Speed is segment-average, count rate is passages/minute, congestion is a synthetic-baseline proxy.",
            "Late events and reviews recompute event-time windows; previous query snapshots remain.",
        ],
    }
