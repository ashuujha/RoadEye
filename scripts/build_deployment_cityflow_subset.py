"""Build the public metadata-only map fixture from frozen CityFlow S02 predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VEHICLES = (
    ("roadeye_5d01be7368ca57e9a2db", ("c008", "c007", "c009")),
    ("roadeye_0e0b4f50a52b58ae9ec3", ("c008", "c007")),
    ("roadeye_714071559a2b5ce2a24d", ("c006", "c007")),
    ("roadeye_ab1e3b31f713579385c7", ("c007", "c009")),
    ("roadeye_0d40f23565a857108d14", ("c008", "c007")),
    ("roadeye_b9fe8f69ee2d5909bd57", ("c006", "c007")),
    ("roadeye_5229ccd9991653beabda", ("c007", "c009")),
    ("roadeye_e7134e2992dd5b3e8166", ("c007", "c009")),
)
EXPECTED_SOURCE_HASHES = {
    "journeys.json": "d327dbff1202294aa67995eeaba38bf81679a2d243bacd39a18c8b48910b67ca",
    "links.json": "34913e16fe168bcf0c1d91fc878abd1ae56528e35ceb261e7b96b09458c51810",
    "tracklets.json": "76155329b33ae9fe938921c84e363202043a79ec3c5d6757cf372673f9e4ea54",
    "topology.json": "b0f3ba0e259d927255cdde0811bbd064ec6d6be88293c51f8626ea41f684df09",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source: Path, destination: Path) -> None:
    for name, expected in EXPECTED_SOURCE_HASHES.items():
        actual = sha256(source / name)
        if actual != expected:
            raise ValueError(f"Frozen source hash changed for {name}: {actual} != {expected}")

    journeys_by_id = {
        journey["global_id"]: journey for journey in load_json(source / "journeys.json")
    }
    source_links = load_json(source / "links.json")
    source_tracklets = load_json(source / "tracklets.json")
    source_topology = load_json(source / "topology.json")

    selected_journeys = []
    selected_keys: set[str] = set()
    incoming_pairs: set[tuple[str, str]] = set()
    for vehicle_id, expected_cameras in VEHICLES:
        try:
            journey = journeys_by_id[vehicle_id]
        except KeyError as error:
            raise ValueError(f"Missing frozen journey: {vehicle_id}") from error
        cameras = tuple(visit["camera"] for visit in journey["visits"])
        if cameras != expected_cameras:
            raise ValueError(
                f"Frozen route changed for {vehicle_id}: {cameras} != {expected_cameras}"
            )
        if int(journey["camera_count"]) != len(set(expected_cameras)):
            raise ValueError(f"Camera count disagrees with visits for {vehicle_id}")
        keys = [visit["tracklet_key"] for visit in journey["visits"]]
        selected_keys.update(keys)
        incoming_pairs.update(zip(keys, keys[1:], strict=False))
        selected_journeys.append(journey)

    selected_links = [
        link
        for link in source_links
        if (link["from_key"], link["to_key"]) in incoming_pairs
    ]
    actual_pairs = {(link["from_key"], link["to_key"]) for link in selected_links}
    if actual_pairs != incoming_pairs:
        missing = sorted(incoming_pairs - actual_pairs)
        raise ValueError(f"Missing frozen association links: {missing}")

    selected_tracklets = {
        key: source_tracklets[key]
        for key in sorted(selected_keys)
        if key in source_tracklets
    }
    if set(selected_tracklets) != selected_keys:
        missing = sorted(selected_keys - set(selected_tracklets))
        raise ValueError(f"Missing frozen tracklets: {missing}")

    camera_ids = {camera for _, cameras in VEHICLES for camera in cameras}
    selected_topology = {
        "kind": source_topology["kind"],
        "positions": {
            camera: source_topology["positions"][camera] for camera in sorted(camera_ids)
        },
        "source_scenario_center": {
            "latitude": 42.491916,
            "longitude": -90.723723,
            "status": "approximate_center_published_with_cityflow_s02",
        },
    }

    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "journeys.json", selected_journeys)
    write_json(destination / "links.json", selected_links)
    write_json(destination / "tracklets.json", selected_tracklets)
    write_json(destination / "topology.json", selected_topology)

    prepared = {
        "schema_version": 1,
        "source": "frozen CityFlow V2 S02 prediction metadata; no identity ground truth",
        "artifact_sha256": {
            "tracklets.json": sha256(destination / "tracklets.json"),
            "topology.json": sha256(destination / "topology.json"),
        },
    }
    write_json(destination / "prepared.json", prepared)
    run = {
        "schema_version": 1,
        "prepared_sha256": sha256(destination / "prepared.json"),
        "prediction_sha256": {
            "journeys": sha256(destination / "journeys.json"),
            "links": sha256(destination / "links.json"),
        },
        "selection": {
            "kind": "preselected_runtime_predictions_for_reliable_map_rehearsal",
            "vehicle_ids": [vehicle_id for vehicle_id, _ in VEHICLES],
            "changes_association_output": False,
        },
        "source_frozen_artifact_sha256": EXPECTED_SOURCE_HASHES,
    }
    write_json(destination / "run.json", run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Frozen reid-trained-s02 artifact directory")
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("deployment/demo-runtime"),
        help="Tracked metadata-only deployment fixture",
    )
    args = parser.parse_args()
    build(args.source.resolve(), args.destination.resolve())


if __name__ == "__main__":
    main()
