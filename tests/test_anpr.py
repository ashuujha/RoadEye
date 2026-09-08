from __future__ import annotations

import csv
from pathlib import Path

import cv2
import numpy as np
import pytest

from roadeye.anpr import (
    ImageRecord,
    assign_splits,
    box_iou,
    edit_distance,
    detection_metrics,
    load_reviewed_transcriptions,
    normalize_plate_text,
    parse_yolo_label,
    validate_ocr_freeze_reviews,
    validate_ocr_prediction_grid,
    wilson_interval,
)


def record(image_id: str, pixel_hash: str) -> ImageRecord:
    return ImageRecord(
        image_id=image_id,
        image=f"images/{image_id}.png",
        label=f"labels/{image_id}.txt",
        series="plate_crop",
        width=100,
        height=30,
        image_sha256=f"file-{image_id}",
        pixel_sha256=pixel_hash,
        perceptual_hash=f"{int.from_bytes(image_id.encode()):016x}"[-16:],
        label_sha256=f"label-{image_id}",
        boxes_xyxy=((0.0, 0.0, 100.0, 30.0),),
    )


def test_normalization_and_character_error_primitives() -> None:
    assert normalize_plate_text(" dl-8c aa 2242 ") == "DL8CAA2242"
    assert edit_distance("DL8CAA2242", "DL8CAA2242") == 0
    assert edit_distance("DL8CAA224Z", "DL8CAA2242") == 1
    assert box_iou((0, 0, 10, 10), (5, 5, 15, 15)) == pytest.approx(25 / 175)
    assert wilson_interval(52, 55) == pytest.approx(
        [0.8514693945594621, 0.9812767844453155]
    )
    assert wilson_interval(0, 0) is None


def test_ocr_freeze_requires_development_truth_and_sealed_test() -> None:
    counts = validate_ocr_freeze_reviews(
        {"dev-a": "reviewed", "dev-b": "unreadable", "test-a": "suggested"},
        {"dev-a", "dev-b"},
        {"test-a"},
        {"dev-a"},
        minimum_readable=1,
    )
    assert counts == {
        "development_images": 2,
        "development_readable_images": 1,
        "development_unreadable_images": 1,
    }
    with pytest.raises(ValueError, match="Test transcriptions"):
        validate_ocr_freeze_reviews(
            {"dev-a": "reviewed", "test-a": "unreadable"},
            {"dev-a"},
            {"test-a"},
            {"dev-a"},
            minimum_readable=1,
        )


def test_ocr_prediction_grid_rejects_missing_or_duplicate_rows() -> None:
    predictions = [
        {
            "image_id": image_id,
            "variant": variant,
            "split": "development",
        }
        for image_id in ("a", "b")
        for variant in ("color", "gray")
    ]
    assert validate_ocr_prediction_grid(
        predictions, {"a", "b"}, {"color", "gray"}, "development"
    ) == {"images": 2, "predictions": 4}
    with pytest.raises(ValueError, match="coverage mismatch"):
        validate_ocr_prediction_grid(
            predictions[:-1], {"a", "b"}, {"color", "gray"}, "development"
        )
    with pytest.raises(ValueError, match="Duplicate"):
        validate_ocr_prediction_grid(
            [*predictions, predictions[0]],
            {"a", "b"},
            {"color", "gray"},
            "development",
        )


def test_split_keeps_exact_pixel_duplicates_together() -> None:
    records = [record("a", "same"), record("b", "same"), record("c", "other")]
    assignments = assign_splits(
        records,
        {
            "plate_crop": {
                "seed": "test",
                "require_single_box": True,
                "order": ["test", "development"],
                "counts": {"test": 1, "development": None},
            }
        },
    )
    assert assignments["a"] == assignments["b"]


def test_yolo_parser_rejects_invalid_rows(tmp_path: Path) -> None:
    valid = tmp_path / "valid.txt"
    valid.write_text("0 0.5 0.5 0.5 0.5\n", encoding="utf-8")
    assert parse_yolo_label(valid, 100, 40) == ((25.0, 10.0, 75.0, 30.0),)
    valid.write_text("1 0.5 0.5 0.5 0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YOLO"):
        parse_yolo_label(valid, 100, 40)


def test_only_reviewed_hash_bound_transcriptions_become_truth(tmp_path: Path) -> None:
    manifest = {
        "records": [
            {"image_id": "a", "image_sha256": "hash-a", "split": "test"},
            {"image_id": "b", "image_sha256": "hash-b", "split": "test"},
        ]
    }
    path = tmp_path / "truth.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "image_id",
                "image_sha256",
                "split",
                "plate_text",
                "review_status",
                "notes",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "image_id": "a",
                "image_sha256": "hash-a",
                "split": "test",
                "plate_text": "DL 8C AA 2242",
                "review_status": "reviewed",
                "notes": "",
            }
        )
        writer.writerow(
            {
                "image_id": "b",
                "image_sha256": "hash-b",
                "split": "test",
                "plate_text": "MODEL GUESS",
                "review_status": "suggested",
                "notes": "",
            }
        )
    assert load_reviewed_transcriptions(path, manifest) == {"a": "DL8CAA2242"}


def test_decoded_pixels_are_stable_for_split_fixture(tmp_path: Path) -> None:
    image = np.full((5, 8, 3), 127, dtype=np.uint8)
    path = tmp_path / "sample.png"
    assert cv2.imwrite(str(path), image)
    assert cv2.imread(str(path), cv2.IMREAD_COLOR).shape == (5, 8, 3)


def test_detection_metrics_match_each_ground_truth_once() -> None:
    records = [
        {
            "image_id": "one",
            "boxes_xyxy": [[0, 0, 10, 10], [20, 20, 30, 30]],
        }
    ]
    predictions = {
        "one": [
            ([0, 0, 10, 10], 0.9),
            ([0, 0, 10, 10], 0.8),
            ([20, 20, 30, 30], 0.4),
        ]
    }
    metrics = detection_metrics(records, predictions, 0.5, 0.5)
    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
