"""Build explicitly unverified S06 prediction summaries without opening GT."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

S06_DISCLOSURE = "S06 — unverified prediction, no ground truth available"


def _link_summary(link: dict[str, Any] | None) -> dict[str, Any] | None:
    if link is None:
        return None
    return {
        "disclosure": S06_DISCLOSURE,
        "from_tracklet": link["from_key"],
        "to_tracklet": link["to_key"],
        "appearance_similarity": link["similarity"],
        "second_best_similarity": link["second_best_similarity"],
        "ambiguity_margin": link["margin"],
        "temporal_gap_s": link["temporal_gap_s"],
        "distance_m": link["distance_m"],
        "temporal_topology_reason": link["reason"],
        "decision_time_s": link["decision_time_s"],
        "score_kind": link["score_kind"],
        "is_probability": False,
        "verification_status": "UNVERIFIED_NO_GROUND_TRUTH",
    }


def _visit_summary(
    visit: dict[str, Any], incoming: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "disclosure": S06_DISCLOSURE,
        "tracklet_key": visit["tracklet_key"],
        "camera": visit["camera"],
        "first_observed_s": visit["first_observed_s"],
        "identified_at_s": visit["identified_at_s"],
        "last_observed_s": visit["last_observed_s"],
        "reference_position": visit["reference_position"],
        "incoming_link": _link_summary(incoming),
        "source_evidence": [
            {
                "disclosure": S06_DISCLOSURE,
                "camera": sample["camera"],
                "frame": sample["frame"],
                "time_s": sample["time_s"],
                "bbox_xywh": sample["bbox_xywh"],
                "crop": sample["crop"],
                "crop_sha256": sample["crop_sha256"],
                "video": sample["video"],
                "baseline_score": sample["baseline_score"],
                "baseline_score_kind": sample["score_kind"],
                "baseline_score_is_probability": False,
            }
            for sample in visit["evidence_samples"]
        ],
    }


def build_s06_report(
    *,
    journeys: list[dict[str, Any]],
    links: list[dict[str, Any]],
    run: dict[str, Any],
    prepared: dict[str, Any],
    window: dict[str, Any],
    selection: dict[str, Any],
    selection_sha256: str,
) -> dict[str, Any]:
    """Summarize predictions while preserving their unscored status."""
    camera_ids = [camera["camera_id"] for camera in window["cameras"]]
    expected = {f"c0{number}" for number in range(41, 47)}
    if window.get("scenario") != "S06" or set(camera_ids) != expected:
        raise ValueError("S06 report requires all six declared S06 cameras")
    if window.get("disclosure") != S06_DISCLOSURE:
        raise ValueError("S06 window is missing the mandatory disclosure")
    if selection.get("status") != "PASS":
        raise ValueError("Frozen S01/S03 selection did not pass")

    link_by_target = {link["to_key"]: link for link in links}
    if len(link_by_target) != len(links):
        raise ValueError("A tracklet has more than one incoming predicted link")
    distribution = Counter(journey["camera_count"] for journey in journeys)
    maximum = max(distribution, default=0)
    leaders = [
        journey for journey in journeys if journey["camera_count"] == maximum
    ]
    predicted = []
    for journey in leaders:
        visits = [
            _visit_summary(visit, link_by_target.get(visit["tracklet_key"]))
            for visit in journey["visits"]
        ]
        scores = [
            visit["incoming_link"]["appearance_similarity"]
            for visit in visits
            if visit["incoming_link"] is not None
        ]
        predicted.append(
            {
                "disclosure": S06_DISCLOSURE,
                "global_vehicle_id": journey["global_id"],
                "prediction_status": "UNVERIFIED_NO_GROUND_TRUTH",
                "camera_count": journey["camera_count"],
                "cameras_in_time_order": [visit["camera"] for visit in visits],
                "visit_count": len(visits),
                "link_similarity_summary": {
                    "count": len(scores),
                    "minimum": min(scores) if scores else None,
                    "mean": mean(scores) if scores else None,
                    "maximum": max(scores) if scores else None,
                    "kind": "uncalibrated_cosine_similarity_not_probability",
                },
                "visits": visits,
            }
        )

    return {
        "schema_version": 1,
        "status": "UNVERIFIED",
        "disclosure": S06_DISCLOSURE,
        "scope": "S06_complete_six_camera_prediction_with_frozen_S01_S03_policy",
        "ground_truth": {
            "available": False,
            "opened_by_prediction_runner": False,
            "used_at_runtime": False,
            "scoring_performed": False,
        },
        "accuracy_metrics": None,
        "accuracy_metrics_reason": "No released S06 ground truth is locally available.",
        "verified_six_camera_criterion": {
            "status": "FAIL",
            "affected_by_this_run": False,
            "existing_max_fully_verified_consistent_camera_count": 2,
            "reason": "An unscored S06 prediction cannot change a verified criterion.",
        },
        "frozen_selection": {
            "source": "reports/reid-six-camera-repair-selection.json",
            "sha256": selection_sha256,
            "development_scenarios": ["S01", "S03"],
            "policy": selection["selected_policy"],
            "hsv_weight": selection["selected_hsv_weight"],
            "s06_retuning_performed": False,
        },
        "window": {
            "scenario": window["scenario"],
            "partition": window["partition"],
            "start_s": window["start_s"],
            "end_s": window["end_s"],
            "cameras": camera_ids,
            "camera_count": len(camera_ids),
            "baseline_filename": window["baseline_filename"],
            "selection_rule": window["selection_rule"],
        },
        "prediction_summary": {
            "baseline_tracklets": run["baseline_tracklets"],
            "embedded_tracklets": run["embedded_tracklets"],
            "predicted_links": run["predicted_links"],
            "roadeye_global_vehicle_ids": run["global_ids"],
            "multi_camera_predicted_identities": sum(
                journey["camera_count"] > 1 for journey in journeys
            ),
            "camera_span_distribution": {
                str(span): distribution[span] for span in sorted(distribution)
            },
            "maximum_predicted_camera_span": maximum,
            "identities_at_maximum_span": len(leaders),
            "model": prepared["model"],
        },
        "maximum_span_predictions": predicted,
        "demo": {
            "config": "configs/demo-s06.json",
            "launch": (
                ".venv\\Scripts\\python.exe -m roadeye serve "
                "--config configs/demo-s06.json --host 127.0.0.1 --port 8000"
            ),
            "presentation_rule": S06_DISCLOSURE,
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["prediction_summary"]
    lines = [
        "# S06 demo prediction",
        "",
        f"**{S06_DISCLOSURE}**",
        "",
        "This run uses the frozen S01/S03 selection without S06 tuning. It is not "
        "an accuracy result and does not change the verified six-camera FAIL status.",
        "",
        "## Prediction summary",
        "",
        f"- Window: {report['window']['start_s']}–{report['window']['end_s']} seconds across "
        f"{report['window']['camera_count']} cameras.",
        f"- Baseline tracklets: {summary['baseline_tracklets']}.",
        f"- Embedded tracklets: {summary['embedded_tracklets']}.",
        f"- Predicted links: {summary['predicted_links']}.",
        f"- RoadEye global vehicle IDs: {summary['roadeye_global_vehicle_ids']}.",
        f"- Multi-camera predicted identities: {summary['multi_camera_predicted_identities']}.",
        f"- Maximum predicted camera span: {summary['maximum_predicted_camera_span']}.",
        f"- Identities at that span: {summary['identities_at_maximum_span']}.",
        "- Accuracy metrics: none; S06 has no released ground truth.",
        "",
        "## Maximum-span predictions",
        "",
    ]
    for journey in report["maximum_span_predictions"]:
        scores = journey["link_similarity_summary"]
        if scores["count"]:
            score_text = (
                f"min {scores['minimum']:.6f}, mean {scores['mean']:.6f}, "
                f"max {scores['maximum']:.6f}"
            )
        else:
            score_text = "no predicted links"
        lines.extend(
            [
                f"- `{journey['global_vehicle_id']}`: "
                f"{' → '.join(journey['cameras_in_time_order'])}; {score_text}.",
            ]
        )
    lines.extend(
        [
            "",
            "Similarity values are uncalibrated cosine similarities, not probabilities.",
            "",
            "## Run the local test interface",
            "",
            "```powershell",
            report["demo"]["launch"],
            "```",
            "",
            f"The interface must continue to show: **{S06_DISCLOSURE}**",
            "",
        ]
    )
    return "\n".join(lines)
