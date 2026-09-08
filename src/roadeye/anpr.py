"""Indian plate audit, transcription, OCR, and evaluation helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import re
import shutil
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np

from .tracklets import sha256, write_json

PLATE_TEXT = re.compile(r"^[A-Z0-9]+$")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
TRANSCRIPTION_COLUMNS = (
    "image_id",
    "image_sha256",
    "split",
    "plate_text",
    "review_status",
    "notes",
)
GROUND_TRUTH_STATUSES = frozenset({"reviewed", "corrected", "unreadable"})
READABLE_GROUND_TRUTH_STATUSES = frozenset({"reviewed", "corrected"})
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageRecord:
    image_id: str
    image: str
    label: str
    series: str
    width: int
    height: int
    image_sha256: str
    pixel_sha256: str
    perceptual_hash: str
    label_sha256: str
    boxes_xyxy: tuple[tuple[float, float, float, float], ...]


def normalize_plate_text(value: str) -> str:
    """Remove layout punctuation without guessing visually ambiguous characters."""

    return "".join(character for character in value.upper() if character.isalnum())


def edit_distance(source: str, target: str) -> int:
    previous = list(range(len(target) + 1))
    for source_index, source_character in enumerate(source, 1):
        current = [source_index]
        for target_index, target_character in enumerate(target, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[target_index] + 1,
                    previous[target_index - 1]
                    + (source_character != target_character),
                )
            )
        previous = current
    return previous[-1]


def wilson_interval(
    successes: int, trials: int, z_score: float = 1.959963984540054
) -> list[float] | None:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if trials <= 0 or successes < 0 or successes > trials:
        return None
    proportion = successes / trials
    denominator = 1 + z_score**2 / trials
    center = (proportion + z_score**2 / (2 * trials)) / denominator
    margin = (
        z_score
        * math.sqrt(
            proportion * (1 - proportion) / trials
            + z_score**2 / (4 * trials**2)
        )
        / denominator
    )
    return [max(0.0, center - margin), min(1.0, center + margin)]


def parse_yolo_label(path: Path, width: int, height: int) -> tuple[tuple[float, ...], ...]:
    boxes = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        columns = line.split()
        if len(columns) != 5 or columns[0] != "0":
            raise ValueError(f"Invalid YOLO label at {path}:{line_number}")
        center_x, center_y, box_width, box_height = map(float, columns[1:])
        if not np.isfinite([center_x, center_y, box_width, box_height]).all():
            raise ValueError(f"Non-finite YOLO label at {path}:{line_number}")
        if not all(0 <= value <= 1 for value in (center_x, center_y)):
            raise ValueError(f"YOLO center outside image at {path}:{line_number}")
        if not 0 < box_width <= 1 or not 0 < box_height <= 1:
            raise ValueError(f"Invalid YOLO dimensions at {path}:{line_number}")
        left = max(0.0, (center_x - box_width / 2) * width)
        top = max(0.0, (center_y - box_height / 2) * height)
        right = min(float(width), (center_x + box_width / 2) * width)
        bottom = min(float(height), (center_y + box_height / 2) * height)
        if right <= left or bottom <= top:
            raise ValueError(f"Empty YOLO box at {path}:{line_number}")
        boxes.append((left, top, right, bottom))
    if not boxes:
        raise ValueError(f"No boxes in {path}")
    return tuple(boxes)


def pixel_sha256(image: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(image.shape, dtype=np.int64).tobytes())
    digest.update(np.ascontiguousarray(image).tobytes())
    return digest.hexdigest()


def perceptual_hash(image: np.ndarray) -> str:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    coefficients = cv2.dct(np.float32(resized))[:8, :8].flatten()[1:]
    median = float(np.median(coefficients))
    value = sum((float(coefficient) > median) << index for index, coefficient in enumerate(coefficients))
    return f"{value:016x}"


def inventory_dataset(dataset_root: Path) -> tuple[list[ImageRecord], dict]:
    image_root = dataset_root / "images"
    label_root = dataset_root / "labels"
    images = {
        path.stem: path
        for path in image_root.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }
    labels = {path.stem: path for path in label_root.glob("*.txt")}
    paired_ids = sorted(images.keys() & labels.keys())
    records = []
    for image_id in paired_ids:
        image_path = images[image_id]
        label_path = labels[image_id]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Unreadable image: {image_path}")
        height, width = image.shape[:2]
        records.append(
            ImageRecord(
                image_id=image_id,
                image=image_path.relative_to(dataset_root).as_posix(),
                label=label_path.relative_to(dataset_root).as_posix(),
                series="scene" if image_path.suffix.lower() == ".jpg" else "plate_crop",
                width=width,
                height=height,
                image_sha256=sha256(image_path),
                pixel_sha256=pixel_sha256(image),
                perceptual_hash=perceptual_hash(image),
                label_sha256=sha256(label_path),
                boxes_xyxy=parse_yolo_label(label_path, width, height),
            )
        )
    missing_labels = sorted(images.keys() - labels.keys())
    missing_images = sorted(labels.keys() - images.keys())
    return records, {
        "decodable_images": len(images),
        "label_files": len(labels),
        "paired_images": len(records),
        "images_without_labels": missing_labels,
        "labels_without_images": missing_images,
    }


def _rank(record: ImageRecord, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{record.pixel_sha256}".encode()).hexdigest()


def benchmark_family_ids(records: list[ImageRecord], policy: dict) -> dict[str, str]:
    """Join exact duplicates and conservative configured perceptual neighbors."""

    result = {}
    for series, settings in policy.items():
        eligible = [record for record in records if record.series == series]
        parent = {record.image_id: record.image_id for record in eligible}

        def find(image_id: str) -> str:
            while parent[image_id] != image_id:
                parent[image_id] = parent[parent[image_id]]
                image_id = parent[image_id]
            return image_id

        def union(first: str, second: str) -> None:
            left, right = find(first), find(second)
            if left != right:
                parent[max(left, right)] = min(left, right)

        exact: dict[str, str] = {}
        for record in eligible:
            if record.pixel_sha256 in exact:
                union(record.image_id, exact[record.pixel_sha256])
            else:
                exact[record.pixel_sha256] = record.image_id
        cutoff = settings.get("near_duplicate_hamming", 0)
        if cutoff:
            for index, first in enumerate(eligible):
                first_hash = int(first.perceptual_hash, 16)
                for second in eligible[index + 1 :]:
                    if (first_hash ^ int(second.perceptual_hash, 16)).bit_count() <= cutoff:
                        union(first.image_id, second.image_id)
        groups: dict[str, list[str]] = defaultdict(list)
        for record in eligible:
            groups[find(record.image_id)].append(record.image_id)
        for members in groups.values():
            family_id = hashlib.sha256("\n".join(sorted(members)).encode()).hexdigest()
            for image_id in members:
                result[image_id] = family_id
    return result


def assign_splits(records: list[ImageRecord], policy: dict) -> dict[str, str]:
    """Assign exact-pixel families together before any transcription is opened."""

    result: dict[str, str] = {}
    family_ids = benchmark_family_ids(records, policy)
    for series, settings in policy.items():
        eligible = [
            record
            for record in records
            if record.series == series
            and (settings.get("require_single_box", False) is False or len(record.boxes_xyxy) == 1)
        ]
        families: dict[str, list[ImageRecord]] = defaultdict(list)
        for record in eligible:
            families[family_ids[record.image_id]].append(record)
        representatives = sorted(
            (members[0] for members in families.values()),
            key=lambda record: _rank(record, settings["seed"]),
        )
        cursor = 0
        for split in settings["order"]:
            count = settings["counts"].get(split)
            selected = representatives[cursor:] if count is None else representatives[cursor : cursor + count]
            cursor += len(selected)
            for representative in selected:
                for member in families[family_ids[representative.image_id]]:
                    result[member.image_id] = split
    return result


def build_audit(config: dict, root: Path) -> tuple[dict, dict]:
    dataset_root = root / config["dataset_root"]
    records, inventory = inventory_dataset(dataset_root)
    benchmark_families = benchmark_family_ids(records, config["splits"])
    assignments = assign_splits(records, config["splits"])
    pixel_counts = Counter(record.pixel_sha256 for record in records)
    file_counts = Counter(record.image_sha256 for record in records)
    series_counts = Counter(record.series for record in records)
    representatives = {
        family_id: min(
            record.image_id
            for record in records
            if benchmark_families[record.image_id] == family_id
        )
        for family_id in set(benchmark_families.values())
    }
    split_file_counts = Counter(assignments.values())
    split_family_counts = Counter(
        assignments[record.image_id]
        for record in records
        if record.image_id == representatives[benchmark_families[record.image_id]]
    )
    box_counts = Counter(
        record.series for record in records for _ in record.boxes_xyxy
    )
    manifest = {
        "schema_version": 1,
        "dataset": "kedarsai_indian_license_plates_with_labels_v1",
        "archive": config["archive"],
        "archive_sha256": sha256(root / config["archive"]),
        "split_policy": config["splits"],
        "records": [
            {
                **record.__dict__,
                "boxes_xyxy": [list(box) for box in record.boxes_xyxy],
                "split": assignments.get(record.image_id, "excluded"),
                "exact_pixel_family": record.pixel_sha256,
                "benchmark_family": benchmark_families[record.image_id],
                "family_representative": (
                    record.image_id
                    == representatives[benchmark_families[record.image_id]]
                ),
            }
            for record in records
        ],
    }
    report = {
        "status": "PASS",
        "scope": "image_box_inventory_and_pretranscription_split_freeze",
        **inventory,
        "series_counts": dict(series_counts),
        "box_counts": dict(box_counts),
        "split_file_counts": dict(split_file_counts),
        "split_independent_family_counts": dict(split_family_counts),
        "excluded_paired_images": len(records) - len(assignments),
        "exact_file_duplicate_images": sum(count - 1 for count in file_counts.values()),
        "exact_pixel_duplicate_images": sum(count - 1 for count in pixel_counts.values()),
        "unique_pixel_images": len(pixel_counts),
        "independent_benchmark_families": len(set(benchmark_families.values())),
        "perceptual_scene_family_policy": "64-bit DCT hash Hamming distance <= 4, connected components",
        "ocr_transcriptions_present": False,
        "ocr_accuracy_status": "UNVERIFIED_pending_reviewed_transcriptions",
        "limitations": [
            "YOLO labels contain boxes only; no plate strings are supplied",
            "PNG plate crops and JPEG scene images measure different capabilities",
            "perceptual near-duplicate review is still required before final OCR claims",
        ],
    }
    return manifest, report


def initialize_transcriptions(manifest: dict, destination: Path) -> int:
    existing = {}
    if destination.exists():
        with destination.open(newline="", encoding="utf-8") as stream:
            existing = {row["image_id"]: row for row in csv.DictReader(stream)}
    selected = [
        record
        for record in manifest["records"]
        if record["series"] == "plate_crop" and record["split"] in {"development", "test"}
        and record["family_representative"]
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=TRANSCRIPTION_COLUMNS)
        writer.writeheader()
        for record in sorted(selected, key=lambda value: (value["split"], value["image_id"])):
            previous = existing.get(record["image_id"], {})
            writer.writerow(
                {
                    "image_id": record["image_id"],
                    "image_sha256": record["image_sha256"],
                    "split": record["split"],
                    "plate_text": previous.get("plate_text", ""),
                    "review_status": previous.get("review_status", ""),
                    "notes": previous.get("notes", ""),
                }
            )
    return len(selected)


def load_reviewed_transcriptions(path: Path, manifest: dict) -> dict[str, str]:
    expected = {record["image_id"]: record for record in manifest["records"]}
    reviewed = {}
    seen = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            image_id = row["image_id"]
            if image_id in seen or image_id not in expected:
                raise ValueError(f"Unknown or duplicate transcription row: {image_id}")
            seen.add(image_id)
            if row["image_sha256"] != expected[image_id]["image_sha256"]:
                raise ValueError(f"Transcription image hash mismatch: {image_id}")
            if row["split"] != expected[image_id]["split"]:
                raise ValueError(f"Transcription split mismatch: {image_id}")
            if row.get("review_status", "") not in READABLE_GROUND_TRUTH_STATUSES:
                continue
            text = normalize_plate_text(row["plate_text"])
            if not text or not PLATE_TEXT.fullmatch(text):
                raise ValueError(f"Invalid reviewed plate text: {image_id}")
            reviewed[image_id] = text
    return reviewed


def preprocess_plate(image: np.ndarray, variant: str) -> np.ndarray:
    if image is None or not image.size:
        raise ValueError("Empty plate image")
    scale = max(1.0, 80.0 / image.shape[0])
    resized = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )
    if variant == "color_upscale":
        return resized
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    if variant == "clahe":
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    if variant == "otsu":
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        return cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    raise ValueError(f"Unknown preprocessing variant: {variant}")


def crop_box(image: np.ndarray, box: Iterable[float], padding: float = 0.03) -> np.ndarray:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    x1 = max(0, int(np.floor(left - width * padding)))
    y1 = max(0, int(np.floor(top - height * padding)))
    x2 = min(image.shape[1], int(np.ceil(right + width * padding)))
    y2 = min(image.shape[0], int(np.ceil(bottom + height * padding)))
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Invalid crop box")
    return image[y1:y2, x1:x2]


def recognize_full_crop(reader: object, image: np.ndarray) -> tuple[str, float]:
    height, width = image.shape[:2]
    result = reader.recognize(
        image,
        horizontal_list=[[0, width, 0, height]],
        free_list=[],
        decoder="beamsearch",
        beamWidth=5,
        batch_size=1,
        workers=0,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        detail=1,
        paragraph=False,
        reformat=True,
    )
    if not result:
        return "", 0.0
    _box, text, score = max(result, key=lambda row: float(row[2]))
    return normalize_plate_text(text), float(score)


def run_ocr(
    records: list[dict],
    dataset_root: Path,
    variants: list[str],
    reader: object,
    clock: Callable[[], float] = time.perf_counter,
) -> list[dict]:
    predictions = []
    for index, record in enumerate(records, 1):
        image = cv2.imread(str(dataset_root / record["image"]), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Unreadable image: {record['image']}")
        plate = crop_box(image, record["boxes_xyxy"][0])
        for variant in variants:
            prepared = preprocess_plate(plate, variant)
            start = clock()
            text, score = recognize_full_crop(reader, prepared)
            predictions.append(
                {
                    "image_id": record["image_id"],
                    "split": record["split"],
                    "variant": variant,
                    "text": text,
                    "score": score,
                    "latency_ms": (clock() - start) * 1000,
                }
            )
        if index % 10 == 0 or index == len(records):
            LOGGER.info(
                "ocr_progress images=%d total=%d predictions=%d",
                index,
                len(records),
                len(predictions),
            )
    return predictions


def evaluate_ocr(predictions: list[dict], truth: dict[str, str], split: str) -> dict:
    selected = [
        row for row in predictions if row["split"] == split and row["image_id"] in truth
    ]
    if not selected:
        return {"status": "UNVERIFIED", "reason": "no_reviewed_transcriptions"}
    variants = sorted({row["variant"] for row in selected})
    results = {}
    for variant in variants:
        rows = [row for row in selected if row["variant"] == variant]
        exact = sum(row["text"] == truth[row["image_id"]] for row in rows)
        characters = sum(len(truth[row["image_id"]]) for row in rows)
        edits = sum(
            edit_distance(row["text"], truth[row["image_id"]]) for row in rows
        )
        nonempty = sum(bool(row["text"]) for row in rows)
        results[variant] = {
            "images": len(rows),
            "exact_matches": exact,
            "full_string_accuracy": exact / len(rows),
            "full_string_accuracy_wilson95": wilson_interval(exact, len(rows)),
            "character_edits": edits,
            "ground_truth_characters": characters,
            "character_error_rate": edits / characters,
            "nonempty_predictions": nonempty,
            "coverage": nonempty / len(rows),
            "mean_latency_ms": sum(row["latency_ms"] for row in rows) / len(rows),
            "p95_latency_ms": float(
                np.percentile([row["latency_ms"] for row in rows], 95)
            ),
        }
    return {"status": "MEASURED", "split": split, "variants": results}


def validate_ocr_freeze_reviews(
    statuses: dict[str, str],
    development_ids: set[str],
    test_ids: set[str],
    reviewed_ids: set[str],
    minimum_readable: int,
) -> dict[str, int]:
    """Enforce terminal development review while keeping test truth sealed."""

    prematurely_opened_test = {
        image_id
        for image_id in test_ids
        if statuses.get(image_id) in GROUND_TRUTH_STATUSES
    }
    if prematurely_opened_test:
        raise ValueError(
            "Test transcriptions must remain unreviewed until OCR preprocessing is frozen"
        )
    unfinished_development = {
        image_id
        for image_id in development_ids
        if statuses.get(image_id) not in GROUND_TRUTH_STATUSES
    }
    if unfinished_development:
        raise ValueError("All development plate families require terminal review")
    readable_development = development_ids & reviewed_ids
    if len(readable_development) < minimum_readable:
        raise ValueError(
            f"At least {minimum_readable} readable development strings are required"
        )
    return {
        "development_images": len(development_ids),
        "development_readable_images": len(readable_development),
        "development_unreadable_images": len(development_ids - reviewed_ids),
    }


def transcription_status_report(
    path: Path,
    manifest: dict,
    target_ids: set[str],
    split: str,
    minimum_readable: int,
) -> dict:
    """Audit exact human-review statuses before any OCR truth is loaded.

    Blank or absent statuses are missing. Every nonblank value outside the three
    declared states is unrecognized. Neither category can enter a denominator.
    """

    expected = {record["image_id"]: record for record in manifest["records"]}
    status_counts = Counter({status: 0 for status in GROUND_TRUTH_STATUSES})
    missing_status = 0
    unrecognized_status = 0
    unrecognized_values: Counter[str] = Counter()
    seen: set[str] = set()
    seen_targets: set[str] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "review_status" not in reader.fieldnames:
            raise ValueError("Transcription CSV is missing the review_status column")
        for row in reader:
            image_id = row.get("image_id", "")
            if image_id in seen or image_id not in expected:
                raise ValueError(f"Unknown or duplicate transcription row: {image_id}")
            seen.add(image_id)
            if image_id not in target_ids:
                continue
            seen_targets.add(image_id)
            record = expected[image_id]
            if row.get("image_sha256") != record["image_sha256"]:
                raise ValueError(f"Transcription image hash mismatch: {image_id}")
            if row.get("split") != split or record["split"] != split:
                raise ValueError(f"Transcription split mismatch: {image_id}")
            status = row.get("review_status", "")
            if not status.strip():
                missing_status += 1
            elif status in GROUND_TRUTH_STATUSES:
                status_counts[status] += 1
            else:
                unrecognized_status += 1
                unrecognized_values[status] += 1
    missing_status += len(target_ids - seen_targets)
    readable = status_counts["reviewed"] + status_counts["corrected"]
    valid = (
        len(seen_targets) == len(target_ids)
        and missing_status == 0
        and unrecognized_status == 0
        and readable >= minimum_readable
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "scope": f"{split}_human_ground_truth_status_readiness",
        "target_images": len(target_ids),
        "reviewed": status_counts["reviewed"],
        "corrected": status_counts["corrected"],
        "unreadable": status_counts["unreadable"],
        "missing_status": missing_status,
        "unrecognized_status": unrecognized_status,
        "unrecognized_values": dict(sorted(unrecognized_values.items())),
        "readable": readable,
        "minimum_readable": minimum_readable,
        "ground_truth_eligible_statuses": sorted(READABLE_GROUND_TRUTH_STATUSES),
    }


def require_ready_transcription_statuses(report: dict) -> None:
    """Abort sealed scoring after its status report has been persisted."""

    if report["missing_status"]:
        raise ValueError(
            f"OCR scoring aborted: {report['missing_status']} rows have missing review_status"
        )
    if report["unrecognized_status"]:
        raise ValueError(
            "OCR scoring aborted: "
            f"{report['unrecognized_status']} rows have unrecognized review_status values"
        )
    if report["readable"] < report["minimum_readable"]:
        raise ValueError(
            "OCR scoring aborted: "
            f"{report['readable']} readable human-reviewed strings; "
            f"at least {report['minimum_readable']} are required"
        )


def validate_ocr_prediction_grid(
    predictions: list[dict],
    expected_ids: set[str],
    expected_variants: set[str],
    split: str,
) -> dict[str, int]:
    """Require exactly one prediction for every expected image/variant pair."""

    counts = Counter(
        (row.get("image_id"), row.get("variant"))
        for row in predictions
        if row.get("split") == split
    )
    expected = {
        (image_id, variant)
        for image_id in expected_ids
        for variant in expected_variants
    }
    actual = set(counts)
    if actual != expected:
        raise ValueError(
            f"OCR prediction coverage mismatch for {split}: "
            f"missing={len(expected - actual)} unexpected={len(actual - expected)}"
        )
    duplicates = [key for key, count in counts.items() if count != 1]
    if duplicates:
        raise ValueError(f"Duplicate OCR predictions for {split}: {len(duplicates)}")
    if len(predictions) != len(expected):
        raise ValueError(f"Predictions from another split found in {split} artifact")
    return {"images": len(expected_ids), "predictions": len(predictions)}


def box_iou(first: Iterable[float], second: Iterable[float]) -> float:
    a = tuple(first)
    b = tuple(second)
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (
        b[3] - b[1]
    ) - intersection
    return intersection / union if union else 0.0


def match_boxes(
    ground_truth: list[Iterable[float]],
    predictions: list[tuple[Iterable[float], float]],
    iou_threshold: float,
) -> dict:
    """Greedily match confidence-ordered predictions to one GT box each."""

    available = set(range(len(ground_truth)))
    true_positives = false_positives = 0
    for box, _confidence in sorted(predictions, key=lambda row: -row[1]):
        candidates = [
            (box_iou(box, ground_truth[index]), index) for index in available
        ]
        best_iou, best_index = max(candidates, default=(0.0, -1))
        if best_iou >= iou_threshold:
            true_positives += 1
            available.remove(best_index)
        else:
            false_positives += 1
    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": len(available),
    }


def build_detection_dataset(
    manifest: dict, dataset_root: Path, output: Path, workspace_root: Path
) -> dict:
    resolved_output = output.resolve()
    allowed_root = (workspace_root / "artifacts" / "anpr").resolve()
    if not resolved_output.is_relative_to(allowed_root) or resolved_output == allowed_root:
        raise ValueError("Detection dataset output must stay below artifacts/anpr")
    if output.exists():
        shutil.rmtree(output)
    counts = Counter()
    for record in manifest["records"]:
        if record["series"] != "scene" or record["split"] not in {
            "train",
            "development",
            "test",
        } or not record["family_representative"]:
            continue
        split = {"development": "val"}.get(record["split"], record["split"])
        image_source = dataset_root / record["image"]
        label_source = dataset_root / record["label"]
        image_destination = output / "images" / split / image_source.name
        label_destination = output / "labels" / split / label_source.name
        image_destination.parent.mkdir(parents=True, exist_ok=True)
        label_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_source, image_destination)
        shutil.copy2(label_source, label_destination)
        if sha256(image_destination) != record["image_sha256"]:
            raise ValueError(f"Copied image hash mismatch: {record['image_id']}")
        if sha256(label_destination) != record["label_sha256"]:
            raise ValueError(f"Copied label hash mismatch: {record['image_id']}")
        counts[split] += 1
    yaml = (
        f"path: {output.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: license_plate\n"
    )
    (output / "data.yaml").write_text(yaml, encoding="utf-8")
    return dict(counts)


def detection_metrics(
    records: list[dict],
    predictions: dict[str, list[tuple[Iterable[float], float]]],
    confidence_threshold: float,
    iou_threshold: float,
) -> dict:
    totals = Counter()
    for record in records:
        selected = [
            row
            for row in predictions.get(record["image_id"], [])
            if row[1] >= confidence_threshold
        ]
        totals.update(match_boxes(record["boxes_xyxy"], selected, iou_threshold))
    true_positives = totals["true_positives"]
    false_positives = totals["false_positives"]
    false_negatives = totals["false_negatives"]
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else None
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else None
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
    )
    return {
        "images": len(records),
        "ground_truth_boxes": sum(len(record["boxes_xyxy"]) for record in records),
        **dict(totals),
        "precision": precision,
        "precision_wilson95": wilson_interval(
            true_positives, true_positives + false_positives
        ),
        "recall": recall,
        "recall_wilson95": wilson_interval(
            true_positives, true_positives + false_negatives
        ),
        "f1": f1,
        "confidence_threshold": confidence_threshold,
        "iou_threshold": iou_threshold,
    }


def write_predictions(path: Path, predictions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, allow_nan=False) + "\n" for row in predictions),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_audit(config: dict, root: Path) -> tuple[dict, dict]:
    manifest, report = build_audit(config, root)
    write_json(root / config["split_manifest"], manifest)
    write_json(root / config["audit_report"], report)
    return manifest, report
