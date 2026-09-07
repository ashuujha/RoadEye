"""Causal, append-only global identity assignment from predicted observations."""

from __future__ import annotations

import math
import uuid
from collections import Counter
from dataclasses import asdict

import numpy as np

from .tracklets import Observation


def distance_m(a: dict, b: dict) -> float:
    lat1, lat2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(math.radians(b["longitude"] - a["longitude"]) / 2) ** 2
    )
    return 6371000 * 2 * math.asin(min(1.0, math.sqrt(h)))


def topology(positions: dict, policy: dict) -> dict:
    return {
        "kind": "calibration_proximity_graph_not_verified_road_connectivity",
        "positions": positions,
        "edges": [
            {
                "from_camera": a,
                "to_camera": b,
                "distance_m": distance_m(positions[a], positions[b]),
            }
            for a in sorted(positions)
            for b in sorted(positions)
            if a != b
            and distance_m(positions[a], positions[b])
            <= policy["max_camera_distance_m"]
        ],
    }


def transition(
    prior: Observation, current: Observation, positions: dict, policy: dict
) -> tuple[bool, str, float]:
    if prior.key.split("/")[:2] != current.key.split("/")[:2]:
        return False, "different_partition_or_scenario", 0.0
    if prior.camera == current.camera:
        return False, "same_camera", 0.0
    gap = current.time_s - prior.time_s
    distance = distance_m(positions[prior.camera], positions[current.camera])
    if gap < 0:
        return False, "future_observation", distance
    if gap > policy["max_gap_s"]:
        return False, "stale_observation", distance
    if distance > policy["max_camera_distance_m"]:
        return False, "outside_proximity_topology", distance
    if distance <= policy["overlap_distance_m"]:
        return True, "nearby_views_may_overlap", distance
    reachable = policy["position_tolerance_m"] + policy["max_speed_mps"] * (
        gap + policy["clock_tolerance_s"]
    )
    if distance > reachable:
        return False, "implausible_travel_time", distance
    return True, "forward_time_and_distance_bound", distance


def associate(
    observations: list[Observation],
    metadata: dict,
    embeddings: dict[str, np.ndarray],
    positions: dict,
    policy: dict,
) -> dict:
    """Use first-K features only once their final sample has arrived.

    Decisions never change. Track endings are not decision inputs. Baseline
    tracks are an upstream assumption, not RoadEye ground-truth identities.
    """
    if set(metadata) != set(embeddings):
        raise ValueError("Embedding/metadata keys differ")
    if not 0 <= policy["margin"] <= 2 or not -1 <= policy["min_similarity"] <= 1:
        raise ValueError("Invalid similarity policy")
    for key, feature in embeddings.items():
        if not np.isfinite(feature).all() or abs(np.linalg.norm(feature) - 1) > 1e-4:
            raise ValueError(f"Invalid normalized embedding: {key}")
        sample_times = [s["time_s"] for s in metadata[key]["samples"]]
        if not sample_times or max(sample_times) != metadata[key]["ready_s"]:
            raise ValueError("Appearance readiness does not match sample timestamps")
    assignments: dict[str, str] = {}
    groups: dict[str, list[str]] = {}
    latest: dict[str, Observation] = {}
    links, decisions = [], []
    for current in sorted(
        observations, key=lambda r: (r.time_s, r.camera, r.frame, r.key)
    ):
        key = current.key
        if key not in metadata:
            continue
        latest[key] = current
        if key in assignments or current.time_s < metadata[key]["ready_s"]:
            continue
        if current.time_s != metadata[key]["ready_s"]:
            raise ValueError(f"Missing appearance-ready observation: {key}")
        candidates = []
        rejected: Counter = Counter()
        for global_id, members in groups.items():
            # No silent same-camera fragment merges through transitive chains.
            if current.camera in {latest[m].camera for m in members}:
                rejected["camera_already_in_group"] += 1
                continue
            options = []
            inconsistent = False
            for member in members:
                prior = latest[member]
                allowed, reason, distance = transition(
                    prior, current, positions, policy
                )
                if reason in {
                    "different_partition_or_scenario",
                    "future_observation",
                    "implausible_travel_time",
                }:
                    inconsistent = True
                if not allowed:
                    rejected[reason] += 1
                    continue
                similarity = float(
                    np.clip(np.dot(embeddings[member], embeddings[key]), -1, 1)
                )
                options.append((similarity, member, distance, reason))
            if inconsistent:
                rejected["group_time_conflict"] += 1
                continue
            if options:
                similarity, member, distance, reason = max(
                    options, key=lambda x: (x[0], x[1])
                )
                candidates.append(
                    {
                        "global_id": global_id,
                        "from_key": member,
                        "similarity": similarity,
                        "distance_m": distance,
                        "reason": reason,
                    }
                )
        candidates.sort(key=lambda x: (-x["similarity"], x["global_id"]))
        best = candidates[0] if candidates else None
        second = candidates[1]["similarity"] if len(candidates) > 1 else None
        difference = best["similarity"] - second if second is not None else None
        accepted = (
            best is not None
            and best["similarity"] >= policy["min_similarity"]
            and (difference is None or difference >= policy["margin"])
        )
        if accepted:
            global_id = best["global_id"]
            prior = latest[best["from_key"]]
            links.append(
                {
                    **best,
                    "to_key": key,
                    "decision_time_s": current.time_s,
                    "temporal_gap_s": current.time_s - prior.time_s,
                    "second_best_similarity": second,
                    "margin": difference,
                    "score_kind": "uncalibrated_cosine_similarity_not_probability",
                    "from_evidence": asdict(prior),
                    "to_evidence": asdict(current),
                    "from_appearance_samples": metadata[prior.key]["samples"],
                    "to_appearance_samples": metadata[key]["samples"],
                }
            )
        else:
            global_id = (
                "roadeye_"
                + uuid.uuid5(uuid.NAMESPACE_URL, "roadeye/phase2/" + key).hex[:20]
            )
            groups[global_id] = []
        assignments[key] = global_id
        groups[global_id].append(key)
        decisions.append(
            {
                "key": key,
                "global_id": global_id,
                "decision_time_s": current.time_s,
                "action": "link" if accepted else "new_identity",
                "reason": (
                    "accepted"
                    if accepted
                    else "no_temporally_eligible_candidate"
                    if not best
                    else "below_similarity_threshold"
                    if best["similarity"] < policy["min_similarity"]
                    else "ambiguous_group_margin"
                ),
                "top_candidates": candidates[:3],
                "rejected_candidate_counts": dict(rejected),
            }
        )
    journeys = []
    for global_id, members in groups.items():
        visits = [
            {
                "tracklet_key": key,
                "camera": metadata[key]["camera"],
                "first_observed_s": metadata[key].get(
                    "first_observed_s", metadata[key]["samples"][0]["time_s"]
                ),
                "identified_at_s": metadata[key]["ready_s"],
                "last_observed_s": latest[key].time_s,
                "reference_position": positions[metadata[key]["camera"]],
                "evidence_samples": metadata[key]["samples"],
            }
            for key in members
        ]
        visits.sort(
            key=lambda x: (x["first_observed_s"], x["camera"], x["tracklet_key"])
        )
        journeys.append(
            {
                "global_id": global_id,
                "visits": visits,
                "camera_count": len({v["camera"] for v in visits}),
                "geometry_status": "observations_only_no_road_route_claim",
            }
        )
    return {
        "assignments": assignments,
        "links": links,
        "decisions": decisions,
        "journeys": journeys,
    }
