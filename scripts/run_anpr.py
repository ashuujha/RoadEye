"""Run explicit RoadEye Indian-plate audit, OCR preparation, and evaluation."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import logging
import socket
import urllib.request
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import easyocr
import numpy as np
from ultralytics import YOLO

from roadeye.anpr import (
    evaluate_ocr,
    build_detection_dataset,
    detection_metrics,
    initialize_transcriptions,
    load_reviewed_transcriptions,
    read_json,
    run_ocr,
    save_audit,
    validate_ocr_freeze_reviews,
    validate_ocr_prediction_grid,
    write_predictions,
)
from roadeye.phase2 import ROOT
from roadeye.tracklets import sha256, text_sha256, write_json


def load_config(path: Path) -> dict:
    return read_json(path)


def audit(config: dict) -> None:
    manifest, report = save_audit(config, ROOT)
    rows = initialize_transcriptions(manifest, ROOT / config["transcriptions"])
    print(json.dumps({**report, "transcription_rows_initialized": rows}, indent=2))


def reader(config: dict, allow_download: bool) -> easyocr.Reader:
    model_directory = ROOT / config["model_directory"]
    model_directory.mkdir(parents=True, exist_ok=True)
    return easyocr.Reader(
        config["ocr"]["languages"],
        gpu=False,
        model_storage_directory=str(model_directory),
        recog_network=config["ocr"]["recognition_network"],
        download_enabled=allow_download,
        detector=False,
        recognizer=True,
        verbose=False,
    )


def prepare(config: dict) -> None:
    reader(config, allow_download=True)
    models = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted((ROOT / config["model_directory"]).glob("*"))
        if path.is_file()
    }
    if not models:
        raise RuntimeError("EasyOCR preparation produced no local model files")
    write_json(
        ROOT / "reports/anpr-models.json",
        {
            "status": "PASS",
            "scope": "explicit_easyocr_recognition_model_preparation",
            "runtime_download_enabled": False,
            "models": models,
        },
    )
    print(json.dumps(models, indent=2))


def prepare_detector(config: dict) -> None:
    destination = ROOT / config["detector"]["initial_weights"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_suffix(destination.suffix + ".part")
        logging.info("detector_download source=%s", config["detector"]["initial_weights_url"])
        with urllib.request.urlopen(
            config["detector"]["initial_weights_url"], timeout=60
        ) as response, temporary.open("wb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        temporary.replace(destination)
    model = YOLO(str(destination))
    if not model.names:
        raise RuntimeError("Downloaded detector checkpoint did not load")
    report = {
        "status": "PASS",
        "scope": "explicit_ultralytics_initial_checkpoint_preparation",
        "runtime_download_enabled": False,
        "source": config["detector"]["initial_weights_url"],
        "file": config["detector"]["initial_weights"],
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }
    write_json(ROOT / "reports/anpr-detector-model.json", report)
    print(json.dumps(report, indent=2))


def build_detector(config: dict) -> None:
    manifest = read_json(ROOT / config["split_manifest"])
    counts = build_detection_dataset(
        manifest,
        ROOT / config["dataset_root"],
        ROOT / config["detector"]["dataset_directory"],
        ROOT,
    )
    report = {
        "status": "PASS",
        "scope": "hash_verified_scene_only_detection_dataset",
        "counts": counts,
        "test_not_referenced_by_training_yaml": True,
    }
    write_json(ROOT / "reports/anpr-detector-dataset.json", report)
    print(json.dumps(report, indent=2))


def train_detector(config: dict) -> None:
    detector = config["detector"]
    model = YOLO(str(ROOT / detector["initial_weights"]))
    result = model.train(
        data=str(ROOT / detector["dataset_directory"] / "data.yaml"),
        epochs=detector["epochs"],
        imgsz=detector["image_size"],
        batch=detector["batch_size"],
        device="cpu",
        workers=0,
        seed=detector["seed"],
        deterministic=True,
        project=str(ROOT / detector["run_directory"]),
        name="roadeye",
        exist_ok=True,
        plots=False,
        verbose=False,
    )
    best = Path(result.save_dir) / "weights/best.pt"
    if not best.exists():
        raise RuntimeError("Detector training produced no best checkpoint")
    report = {
        "status": "PASS",
        "scope": "scene_train_and_development_only_detector_training",
        "device": "cpu",
        "epochs_requested": detector["epochs"],
        "initial_weights_sha256": sha256(ROOT / detector["initial_weights"]),
        "best_weights": best.relative_to(ROOT).as_posix(),
        "best_weights_sha256": sha256(best),
        "test_opened": False,
    }
    write_json(ROOT / "reports/anpr-detector-training.json", report)
    print(json.dumps(report, indent=2))


def _detector_predictions(model: YOLO, records: list[dict], config: dict) -> tuple[dict, list[float]]:
    images = [str(ROOT / config["dataset_root"] / record["image"]) for record in records]
    results = model.predict(
        source=images,
        imgsz=config["detector"]["image_size"],
        conf=min(config["detector"]["confidence_grid"]),
        device="cpu",
        stream=False,
        verbose=False,
    )
    predictions = {}
    latencies = []
    for record, result in zip(records, results, strict=True):
        predictions[record["image_id"]] = [
            (box, confidence)
            for box, confidence in zip(
                result.boxes.xyxy.cpu().numpy().tolist(),
                result.boxes.conf.cpu().numpy().tolist(),
                strict=True,
            )
        ]
        latencies.append(float(sum(result.speed.values())))
    return predictions, latencies


def evaluate_detector(config: dict) -> None:
    manifest = read_json(ROOT / config["split_manifest"])
    detector = config["detector"]
    training = read_json(ROOT / "reports/anpr-detector-training.json")
    best = ROOT / training["best_weights"]
    if sha256(best) != training["best_weights_sha256"]:
        raise ValueError("Detector weight hash mismatch")
    model = YOLO(str(best))
    development_records = [
        row
        for row in manifest["records"]
        if row["series"] == "scene"
        and row["split"] == "development"
        and row["family_representative"]
    ]
    development_predictions, development_latency = _detector_predictions(
        model, development_records, config
    )
    candidates = [
        detection_metrics(
            development_records,
            development_predictions,
            threshold,
            detector["iou_threshold"],
        )
        for threshold in detector["confidence_grid"]
    ]
    selected = max(candidates, key=lambda row: (row["f1"], row["confidence_threshold"]))
    selection = {
        "status": "PASS",
        "scope": "development_only_detector_confidence_selection_before_test",
        "best_weights_sha256": training["best_weights_sha256"],
        "selected_confidence_threshold": selected["confidence_threshold"],
        "development_candidates": candidates,
        "development_mean_latency_ms": float(np.mean(development_latency)),
    }
    write_json(ROOT / "reports/anpr-detector-selection.json", selection)
    test_records = [
        row
        for row in manifest["records"]
        if row["series"] == "scene"
        and row["split"] == "test"
        and row["family_representative"]
    ]
    test_predictions, test_latency = _detector_predictions(model, test_records, config)
    metrics = detection_metrics(
        test_records,
        test_predictions,
        selected["confidence_threshold"],
        detector["iou_threshold"],
    )
    report = {
        "status": "MEASURED",
        "scope": "frozen_independent_scene_test_split_plate_detection",
        **metrics,
        "mean_cpu_latency_ms": float(np.mean(test_latency)),
        "p95_cpu_latency_ms": float(np.percentile(test_latency, 95)),
        "best_weights_sha256": training["best_weights_sha256"],
        "limitations": [
            "Small local test split from one Kaggle dataset",
            "Near-duplicate scene review is not yet complete",
            "This metric measures boxes only, not plate strings",
        ],
    }
    write_json(ROOT / "reports/anpr-detector-test.json", report)
    print(json.dumps(report, indent=2))


def predict(config: dict) -> None:
    manifest = read_json(ROOT / config["split_manifest"])
    selection_path = ROOT / "reports/anpr-ocr-selection.json"
    if selection_path.exists():
        selection = _validate_ocr_selection(selection_path)
        active_split = "test"
        variants = [selection["selected_variant"]]
    else:
        active_split = "development"
        variants = config["ocr"]["variants"]
    records = [
        record
        for record in manifest["records"]
        if record["series"] == "plate_crop"
        and record["split"] == active_split
        and record["family_representative"]
    ]
    predictions = run_ocr(
        records,
        ROOT / config["dataset_root"],
        variants,
        reader(config, allow_download=False),
    )
    destination = ROOT / config[f"{active_split}_predictions"]
    write_predictions(destination, predictions)
    print(
        json.dumps(
            {
                "split": active_split,
                "images": len(records),
                "variants": variants,
                "predictions": len(predictions),
                "destination": destination.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


def _read_predictions(config: dict, split: str) -> list[dict]:
    path = ROOT / config[f"{split}_predictions"]
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _validate_ocr_selection(path: Path) -> dict:
    selection = read_json(path)
    if selection.get("status") != "PASS":
        raise ValueError("OCR selection report is not a passing freeze")
    for relative, expected in selection["frozen_sha256"].items():
        source = ROOT / relative
        actual = (
            text_sha256(source)
            if source.suffix in {".json", ".py"}
            else sha256(source)
        )
        if actual != expected:
            raise ValueError(f"Frozen OCR input changed: {relative}")
    return selection


def build_review(config: dict) -> None:
    manifest = read_json(ROOT / config["split_manifest"])
    selection_path = ROOT / "reports/anpr-ocr-selection.json"
    if selection_path.exists():
        selection = _validate_ocr_selection(selection_path)
        active_split = "test"
        review_variants = {selection["selected_variant"]}
    else:
        active_split = "development"
        review_variants = set(config["ocr"]["variants"])
    records = {
        record["image_id"]: record
        for record in manifest["records"]
        if record["series"] == "plate_crop"
        and record["split"] == active_split
        and record["family_representative"]
    }
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in _read_predictions(config, active_split):
        if row["image_id"] in records:
            grouped[row["image_id"]].append(row)
    transcription_path = ROOT / config["transcriptions"]
    with transcription_path.open(newline="", encoding="utf-8") as stream:
        transcription_rows = {row["image_id"]: row for row in csv.DictReader(stream)}
    if active_split == "development":
        premature_test_rows = [
            row
            for row in transcription_rows.values()
            if row["split"] == "test"
            and row["review_status"] in {"reviewed", "unreadable"}
        ]
        if premature_test_rows:
            raise ValueError(
                "Test transcriptions must remain unreviewed until OCR preprocessing is frozen"
            )
        for row in transcription_rows.values():
            if row["split"] == "test":
                row["plate_text"] = ""
                row["review_status"] = "pending"
                row["notes"] = ""
    items = []
    for image_id, record in sorted(records.items(), key=lambda row: (row[1]["split"], row[0])):
        candidates = grouped[image_id]
        candidate_variants = {row["variant"] for row in candidates}
        if (
            len(candidates) != len(review_variants)
            or candidate_variants != review_variants
        ):
            raise ValueError(f"Missing OCR suggestions: {image_id}")
        vote_counts = Counter(row["text"] for row in candidates)
        suggestion = max(
            candidates,
            key=lambda row: (vote_counts[row["text"]], row["score"], row["text"]),
        )["text"]
        existing = transcription_rows[image_id]
        if existing["review_status"] == "pending":
            existing["plate_text"] = suggestion
            existing["review_status"] = "suggested"
        image_path = ROOT / config["dataset_root"] / record["image"]
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        items.append(
            {
                "image_id": image_id,
                "image_sha256": record["image_sha256"],
                "split": record["split"],
                "image": f"data:{mime};base64,{base64.b64encode(image_path.read_bytes()).decode()}",
                "plate_text": existing["plate_text"],
                "review_status": existing["review_status"],
                "notes": existing["notes"],
                "suggestions": [
                    {
                        "variant": row["variant"],
                        "text": row["text"],
                        "score": round(row["score"], 6),
                    }
                    for row in candidates
                ],
            }
        )
    with transcription_path.open("w", newline="", encoding="utf-8") as stream:
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
        writer.writerows(transcription_rows.values())
    export_rows = [
        {
            column: row[column]
            for column in (
                "image_id",
                "image_sha256",
                "split",
                "plate_text",
                "review_status",
                "notes",
            )
        }
        for row in transcription_rows.values()
    ]
    template = """<!doctype html><meta charset="utf-8"><title>RoadEye transcription review</title>
<style>body{font:16px system-ui;max-width:1000px;margin:20px auto;background:#f5f5f5;color:#111}main{background:white;padding:20px;border-radius:8px}img{display:block;max-width:100%;max-height:300px;margin:20px auto;image-rendering:auto}input{font:700 28px monospace;width:100%;box-sizing:border-box;padding:10px}button,select{font:inherit;padding:8px;margin:6px}.warn{background:#fff3cd;padding:12px}.suggestions{font-family:monospace;white-space:pre-wrap}</style>
<main><h1>RoadEye __PHASE__ transcription review</h1><p class="warn">Model suggestions are not ground truth. Inspect every character in the image before marking reviewed. Use unreadable when the full string cannot be established.</p><p id="progress"></p><img id="plate"><p id="meta"></p><input id="text" autocomplete="off" spellcheck="false"><p class="suggestions" id="suggestions"></p><select id="status"><option>suggested</option><option>reviewed</option><option>unreadable</option><option>pending</option></select><input id="notes" placeholder="notes"><div><button id="previous">Previous</button><button id="save">Save current</button><button id="review">Mark reviewed + next</button><button id="next">Next</button><button id="export">Export CSV</button></div></main>
<script>const original=__DATA__; const allRows=__ROWS__; const key='roadeye-anpr-review-'+__MANIFEST__+'-'+__PHASE_JSON__; const saved=JSON.parse(localStorage.getItem(key)||'{}'); const items=original.map(x=>Object.assign(x,saved[x.image_id]||{})); let index=0;
const el=id=>document.getElementById(id); function clean(x){return x.toUpperCase().replace(/[^A-Z0-9]/g,'')}; function persist(){const x=items[index]; x.plate_text=clean(el('text').value); x.review_status=el('status').value; x.notes=el('notes').value; saved[x.image_id]={plate_text:x.plate_text,review_status:x.review_status,notes:x.notes}; localStorage.setItem(key,JSON.stringify(saved))}; function render(){const x=items[index]; el('plate').src=x.image; el('text').value=x.plate_text; el('status').value=x.review_status; el('notes').value=x.notes; el('meta').textContent=`${x.image_id} | ${x.split} | ${x.image_sha256.slice(0,12)}`; el('suggestions').textContent=x.suggestions.map(s=>`${s.variant}: ${s.text} (${s.score})`).join('\\n'); el('progress').textContent=`${index+1}/${items.length}; reviewed ${items.filter(x=>x.review_status==='reviewed').length}; unreadable ${items.filter(x=>x.review_status==='unreadable').length}`; el('text').focus(); el('text').select()}; function move(n){persist(); index=Math.max(0,Math.min(items.length-1,index+n)); render()}; el('previous').onclick=()=>move(-1); el('next').onclick=()=>move(1); el('save').onclick=()=>{persist();render()}; el('review').onclick=()=>{el('status').value='reviewed';move(1)}; document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter'){el('review').click()}}); function csvCell(x){return '"'+String(x).replaceAll('"','""')+'"'}; el('export').onclick=()=>{persist(); const columns=['image_id','image_sha256','split','plate_text','review_status','notes']; const byId=Object.fromEntries(items.map(x=>[x.image_id,x])); const rows=allRows.map(x=>Object.assign(x,byId[x.image_id]||{})); const lines=[columns.join(','),...rows.map(x=>columns.map(c=>csvCell(x[c]||'')).join(','))]; const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([lines.join('\\r\\n')+'\\r\\n'],{type:'text/csv'})); a.download='transcriptions.csv';a.click()}; render();</script>"""
    page = template.replace("__DATA__", json.dumps(items).replace("</", "<\\/"))
    page = page.replace("__ROWS__", json.dumps(export_rows).replace("</", "<\\/"))
    page = page.replace("__MANIFEST__", json.dumps(manifest["archive_sha256"][:16]))
    page = page.replace("__PHASE_JSON__", json.dumps(active_split))
    page = page.replace("__PHASE__", active_split)
    destination = ROOT / "artifacts/anpr/transcription-review.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    print(
        json.dumps(
            {
                "items": len(items),
                "active_split": active_split,
                "development": sum(row["split"] == "development" for row in items),
                "test": sum(row["split"] == "test" for row in items),
                "review_page": destination.relative_to(ROOT).as_posix(),
                "transcriptions": config["transcriptions"],
            },
            indent=2,
        )
    )


def evaluate(config: dict) -> None:
    manifest = read_json(ROOT / config["split_manifest"])
    statuses = _review_statuses(ROOT / config["transcriptions"])
    test_ids = {
        row["image_id"]
        for row in manifest["records"]
        if row["series"] == "plate_crop"
        and row["split"] == "test"
        and row["family_representative"]
    }
    if any(
        statuses.get(image_id) in {"reviewed", "unreadable"}
        for image_id in test_ids
    ):
        raise ValueError(
            "Test transcriptions must remain unreviewed until OCR preprocessing is frozen"
        )
    truth = load_reviewed_transcriptions(ROOT / config["transcriptions"], manifest)
    development_ids = {
        row["image_id"]
        for row in manifest["records"]
        if row["series"] == "plate_crop"
        and row["split"] == "development"
        and row["family_representative"]
    }
    predictions = _read_predictions(config, "development")
    validate_ocr_prediction_grid(
        predictions,
        development_ids,
        set(config["ocr"]["variants"]),
        "development",
    )
    development = evaluate_ocr(predictions, truth, "development")
    report = {
        "status": development["status"],
        "scope": "recognition_on_ground_truth_plate_crops",
        "reviewed_transcriptions": len(truth),
        "development": development,
        "test": {
            "status": "UNVERIFIED",
            "reason": "test_preprocessing_must_be_frozen_after_development_review",
        },
        "limitations": [
            "This phase evaluates recognition on supplied plate boxes, not end-to-end scene ANPR",
            "Ground truth must have review_status=reviewed; suggestions are never labels",
            "Scores are EasyOCR confidences and are not calibrated probabilities",
        ],
    }
    write_json(ROOT / "reports/anpr-ocr-development.json", report)
    print(json.dumps(report, indent=2))


def _review_statuses(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        return {row["image_id"]: row["review_status"] for row in csv.DictReader(stream)}


def freeze_ocr(config: dict) -> None:
    manifest = read_json(ROOT / config["split_manifest"])
    statuses = _review_statuses(ROOT / config["transcriptions"])
    development_ids = {
        row["image_id"]
        for row in manifest["records"]
        if row["series"] == "plate_crop"
        and row["split"] == "development"
        and row["family_representative"]
    }
    test_ids = {
        row["image_id"]
        for row in manifest["records"]
        if row["series"] == "plate_crop"
        and row["split"] == "test"
        and row["family_representative"]
    }
    review_counts = validate_ocr_freeze_reviews(
        statuses,
        development_ids,
        test_ids,
        {
            image_id
            for image_id, status in statuses.items()
            if status == "reviewed"
        },
        minimum_readable=40,
    )
    truth = load_reviewed_transcriptions(ROOT / config["transcriptions"], manifest)
    predictions = _read_predictions(config, "development")
    validate_ocr_prediction_grid(
        predictions,
        development_ids,
        set(config["ocr"]["variants"]),
        "development",
    )
    development = evaluate_ocr(predictions, truth, "development")
    selected_variant, selected_metrics = max(
        development["variants"].items(),
        key=lambda row: (
            row[1]["full_string_accuracy"],
            -row[1]["character_error_rate"],
            -row[1]["mean_latency_ms"],
            row[0],
        ),
    )
    model_path = next((ROOT / config["model_directory"]).glob("*.pth"))
    selection = {
        "status": "PASS",
        "scope": "development_only_OCR_preprocessing_selection_before_test_scoring",
        **review_counts,
        "selected_variant": selected_variant,
        "selected_metrics": selected_metrics,
        "all_development_metrics": development["variants"],
        "frozen_sha256": {
            config["split_manifest"]: text_sha256(ROOT / config["split_manifest"]),
            config["development_predictions"]: sha256(
                ROOT / config["development_predictions"]
            ),
            config["model_directory"] + "/" + model_path.name: sha256(model_path),
            "configs/anpr.json": text_sha256(ROOT / "configs/anpr.json"),
            "src/roadeye/anpr.py": text_sha256(ROOT / "src/roadeye/anpr.py"),
            "scripts/run_anpr.py": text_sha256(ROOT / "scripts/run_anpr.py"),
        },
        "test_predictions_scored_before_freeze": False,
    }
    write_json(ROOT / "reports/anpr-ocr-selection.json", selection)
    print(json.dumps(selection, indent=2))


def evaluate_ocr_test(config: dict) -> None:
    selection = _validate_ocr_selection(ROOT / "reports/anpr-ocr-selection.json")
    manifest = read_json(ROOT / config["split_manifest"])
    truth = load_reviewed_transcriptions(ROOT / config["transcriptions"], manifest)
    statuses = _review_statuses(ROOT / config["transcriptions"])
    test_ids = {
        row["image_id"]
        for row in manifest["records"]
        if row["series"] == "plate_crop"
        and row["split"] == "test"
        and row["family_representative"]
    }
    unfinished = {
        image_id
        for image_id in test_ids
        if statuses.get(image_id) not in {"reviewed", "unreadable"}
    }
    if unfinished:
        raise ValueError("All 200 test plate families require terminal review")
    test_truth = test_ids & truth.keys()
    if len(test_truth) < 150:
        raise ValueError("At least 150 readable independent test strings are required")
    predictions = [
        row
        for row in _read_predictions(config, "test")
        if row["variant"] == selection["selected_variant"]
    ]
    prediction_counts = validate_ocr_prediction_grid(
        predictions,
        test_ids,
        {selection["selected_variant"]},
        "test",
    )
    measured = evaluate_ocr(predictions, truth, "test")
    report = {
        "status": "MEASURED",
        "scope": "frozen_independent_plate_crop_full_string_test",
        "selected_variant": selection["selected_variant"],
        "frozen_test_images": len(test_ids),
        "readable_test_images": len(test_truth),
        "unreadable_test_images": len(test_ids - truth.keys()),
        "metrics": measured["variants"][selection["selected_variant"]],
        "prediction_counts": prediction_counts,
        "test_predictions_sha256": sha256(ROOT / config["test_predictions"]),
        "transcription_sha256": sha256(ROOT / config["transcriptions"]),
        "limitations": [
            "Recognition uses supplied plate boxes and is not end-to-end scene ANPR",
            "One manually reviewed local Kaggle test split is not city-wide accuracy",
            "OCR confidence is not a calibrated probability",
        ],
    }
    write_json(ROOT / "reports/anpr-ocr-test.json", report)
    print(json.dumps(report, indent=2))


@contextmanager
def network_blocked():
    """Reject common Python network connection paths during runtime checks."""

    def reject(*_args, **_kwargs):
        raise RuntimeError("Network access blocked by RoadEye offline verification")

    with (
        patch.object(socket.socket, "connect", reject),
        patch.object(socket.socket, "connect_ex", reject),
        patch("socket.create_connection", reject),
        patch("urllib.request.urlopen", reject),
    ):
        yield


def verify_offline(config: dict) -> None:
    """Load cached CPU models with networking blocked and replay inference."""

    manifest = read_json(ROOT / config["split_manifest"])
    training = read_json(ROOT / "reports/anpr-detector-training.json")
    detector_path = ROOT / training["best_weights"]
    if sha256(detector_path) != training["best_weights_sha256"]:
        raise ValueError("Detector weight hash mismatch")
    model_report = read_json(ROOT / "reports/anpr-models.json")
    for filename, metadata in model_report["models"].items():
        model_path = ROOT / config["model_directory"] / filename
        if sha256(model_path) != metadata["sha256"]:
            raise ValueError(f"OCR model hash mismatch: {filename}")

    scene_records = [
        row
        for row in manifest["records"]
        if row["series"] == "scene"
        and row["split"] == "development"
        and row["family_representative"]
    ][:2]
    crop_records = [
        row
        for row in manifest["records"]
        if row["series"] == "plate_crop"
        and row["split"] == "development"
        and row["family_representative"]
    ][:1]
    with network_blocked():
        detector = YOLO(str(detector_path))
        first_boxes, _ = _detector_predictions(detector, scene_records, config)
        second_boxes, _ = _detector_predictions(detector, scene_records, config)
        ocr_reader = reader(config, allow_download=False)
        first_ocr = run_ocr(
            crop_records,
            ROOT / config["dataset_root"],
            config["ocr"]["variants"],
            ocr_reader,
        )
        second_ocr = run_ocr(
            crop_records,
            ROOT / config["dataset_root"],
            config["ocr"]["variants"],
            ocr_reader,
        )

    detector_equal = first_boxes == second_boxes
    first_ocr_values = [
        (row["image_id"], row["variant"], row["text"], row["score"])
        for row in first_ocr
    ]
    second_ocr_values = [
        (row["image_id"], row["variant"], row["text"], row["score"])
        for row in second_ocr
    ]
    ocr_equal = first_ocr_values == second_ocr_values
    if not detector_equal or not ocr_equal:
        raise RuntimeError("Repeated offline inference was not deterministic")
    report = {
        "status": "PASS",
        "scope": "local_cpu_cached_model_offline_integrity",
        "network_guard": "socket_and_urllib_connections_rejected",
        "detector_images": len(scene_records),
        "ocr_images": len(crop_records),
        "ocr_variants": len(config["ocr"]["variants"]),
        "detector_replay_equal": detector_equal,
        "ocr_replay_equal": ocr_equal,
        "detector_weights_sha256": sha256(detector_path),
        "ocr_model_sha256": {
            filename: metadata["sha256"]
            for filename, metadata in model_report["models"].items()
        },
    }
    write_json(ROOT / "reports/anpr-offline-integrity.json", report)
    print(json.dumps(report, indent=2))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "audit",
            "prepare-models",
            "prepare-detector",
            "build-detector",
            "train-detector",
            "evaluate-detector",
            "predict",
            "build-review",
            "evaluate",
            "freeze-ocr",
            "evaluate-ocr-test",
            "verify-offline",
        ],
    )
    parser.add_argument("--config", type=Path, default=ROOT / "configs/anpr.json")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.action == "audit":
        audit(config)
    elif args.action == "prepare-models":
        prepare(config)
    elif args.action == "prepare-detector":
        prepare_detector(config)
    elif args.action == "build-detector":
        build_detector(config)
    elif args.action == "train-detector":
        train_detector(config)
    elif args.action == "evaluate-detector":
        evaluate_detector(config)
    elif args.action == "build-review":
        build_review(config)
    elif args.action == "freeze-ocr":
        freeze_ocr(config)
    elif args.action == "evaluate-ocr-test":
        evaluate_ocr_test(config)
    elif args.action == "verify-offline":
        verify_offline(config)
    elif args.action == "predict":
        predict(config)
    else:
        evaluate(config)


if __name__ == "__main__":
    main()
