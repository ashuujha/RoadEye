"""Bounded, non-greedy candidate DAG; every link is inferred, never a physical-ID assertion."""

from datetime import datetime

POLICY = "graph-v1"


def paths(edges: list[dict], source: str, target: str, max_hops: int = 4) -> list[list[dict]]:
    found: list[list[dict]] = []

    def walk(node: str, used: set[str], path: list[dict]):
        if len(path) >= max_hops or len(found) >= 32:
            return
        for edge in sorted(edges, key=lambda e: (e["source"], e["target"])):
            if edge["source"] != node or edge["target"] in used:
                continue
            next_path = [*path, edge]
            if edge["target"] == target:
                found.append(next_path)
            else:
                walk(edge["target"], used | {edge["target"]}, next_path)

    walk(source, {source}, [])
    return found


def similar(a: str, b: str) -> bool:
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) <= 1


def reconstruct(nodes: list[dict], edges: list[dict], plate: str) -> dict:
    nodes = sorted(nodes, key=lambda n: (n["captured_at"], n["id"]))
    links, rejected, review = [], [], []
    for i, first in enumerate(nodes):
        for second in nodes[i + 1 :]:
            elapsed = (
                datetime.fromisoformat(second["captured_at"])
                - datetime.fromisoformat(first["captured_at"])
            ).total_seconds()
            route_options = paths(edges, first["camera_id"], second["camera_id"])
            base = {
                "from": first["id"],
                "to": second["id"],
                "elapsed_seconds": elapsed,
                "source": first["camera_id"],
                "target": second["camera_id"],
                "observed": False,
            }
            if elapsed == 0 and first["camera_id"] != second["camera_id"]:
                rejected.append({**base, "reason": "SAME_PLATE_COLLISION"})
                continue
            if first["camera_id"] == second["camera_id"]:
                review.append({**base, "reason": "REPEATED_CAMERA_LOOP"})
                continue
            if not route_options:
                rejected.append({**base, "reason": "NO_DIRECTED_PATH"})
                continue
            plausible = []
            for route in route_options:
                minimum = sum(e["min_seconds"] for e in route)
                maximum = sum(e["max_seconds"] for e in route)
                if minimum <= elapsed <= maximum:
                    plausible.append(
                        {
                            "cameras": [first["camera_id"]] + [e["target"] for e in route],
                            "distance_m": sum(e["distance_m"] for e in route),
                            "baseline_seconds": sum(e["baseline_seconds"] for e in route),
                        }
                    )
            if not plausible:
                reason = (
                    "IMPOSSIBLE_TRAVEL"
                    if elapsed < min(sum(e["min_seconds"] for e in p) for p in route_options)
                    else "SESSION_GAP"
                )
                rejected.append({**base, "reason": reason})
                continue
            # Do not bypass an enrolled intermediate sighting when both sublinks are plausible.
            bypass = False
            for middle in nodes[i + 1 :]:
                if middle["captured_at"] >= second["captured_at"]:
                    break
                if any(middle["camera_id"] in p["cameras"][1:-1] for p in plausible):
                    a = (
                        datetime.fromisoformat(middle["captured_at"])
                        - datetime.fromisoformat(first["captured_at"])
                    ).total_seconds()
                    b = elapsed - a

                    def feasible(s, t, duration):
                        return any(
                            sum(e["min_seconds"] for e in p)
                            <= duration
                            <= sum(e["max_seconds"] for e in p)
                            for p in paths(edges, s, t)
                        )

                    if feasible(first["camera_id"], middle["camera_id"], a) and feasible(
                        middle["camera_id"], second["camera_id"], b
                    ):
                        bypass = True
            if bypass:
                continue
            score = min(first["score"], second["score"])
            link = {**base, "routes": plausible, "score": score, "status": "plausible"}
            if (
                first["status"] != "accepted"
                or second["status"] != "accepted"
                or first["plate"] != plate
                or second["plate"] != plate
            ):
                review.append({**link, "reason": "WEAK_PLATE_EVIDENCE"})
            else:
                links.append(link)
    # Preserve every plausible fork/merge, regardless of a marginal score advantage.
    alternatives = []
    for node in nodes:
        outgoing = [link for link in links if link["from"] == node["id"]]
        incoming = [link for link in links if link["to"] == node["id"]]
        for choices in (outgoing, incoming):
            if len(choices) > 1:
                alternatives.append(
                    {
                        "at": node["id"],
                        "links": choices,
                        "reason": "MULTIPLE_PLAUSIBLE_CONTINUATIONS",
                    }
                )
                for link in choices:
                    link["status"] = "ambiguous"
    for link in links:
        if len(link["routes"]) > 1:
            link["status"] = "ambiguous"
            alternatives.append(
                {"at": link["from"], "links": [link], "reason": "MULTIPLE_ROAD_PATHS"}
            )
    return {
        "observed_nodes": nodes,
        "inferred_links": links,
        "review_candidates": review,
        "rejected_links": rejected,
        "alternatives": alternatives,
        "scoring_policy": POLICY,
        "limits": {"max_hops": 4, "max_paths_per_pair": 32},
        "limitations": "Same text is not physical vehicle identity. Routes are inferred; alternatives excluded from definite flow.",
    }
