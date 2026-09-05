"""Read-only reproduction audit; emits aggregates, never plate transcriptions."""

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import av
import cv2
import numpy as np
from roadeye import models as m
from roadeye.config import settings
from roadeye.contracts import Reading
from roadeye.db import SessionLocal
from roadeye.evidence import digest
from roadeye.plates import consensus, normalize
from roadeye.recorded.inference import Recognizer, verify_models
from roadeye.recorded.service import passages, status
from sqlalchemy import select


def audit(run_id: str) -> dict:
    with SessionLocal() as db:
        state = status(db, run_id)
        config = state["config"]
        assert verify_models(settings.model_root) == config["models"]
        assert digest(Path(config["manifest"]["path"]).read_bytes()) == config["manifest"]["sha256"]
        predictions = passages(db, run_id)
        assets = list(db.scalars(select(m.Evidence).where(m.Evidence.run_id == run_id)))
        for asset in assets:
            content = (settings.recorded_evidence_root / asset.object_key).read_bytes()
            assert digest(content) == asset.digest and len(content) == asset.size
        by_pts: dict[int, list] = {}
        ocr = Recognizer(settings.model_root)
        details = []
        reproductions = 0
        for index, passage in enumerate(predictions):
            machine = passage["observation"]["machine"]
            samples = passage["inference"]["samples"]
            readings = []
            for sample in samples:
                asset = db.get(m.Evidence, sample["crop_evidence_id"])
                assert asset
                crop = cv2.imread(str(settings.recorded_evidence_root / asset.object_key))
                inferred = ocr.recognize(crop)
                assert inferred == sample["ocr"], "Stored OCR not reproduced by current adapter"
                reproductions += 1
                by_pts.setdefault(sample["pts"], []).append((sample, crop))
                readings.append(
                    Reading(
                        frame_id=f"pts:{sample['pts']}",
                        candidates=[
                            {"text": inferred["text"], "confidence": inferred["confidence"]}
                        ],
                    )
                )
            decision = consensus(
                readings, 1, 1, machine["thresholds"]["accept"], machine["thresholds"]["margin"]
            )
            assert decision == machine, "Original consensus differs from current policy"
            details.append(
                {
                    "index": index,
                    "seconds": passage["relative_seconds"],
                    "status": passage["observation"]["status"],
                    "samples": len(samples),
                    "supported_readings": sum(
                        bool(normalize(sample["ocr"]["text"])) for sample in samples
                    ),
                    "consensus_score": machine["score"],
                    "reasons": machine["reasons"],
                }
            )
        decoded = processed = checked = 0
        next_sample = 0.0
        with av.open(config["manifest"]["path"]) as source:
            stream = source.streams.video[0]
            for frame in source.decode(stream):
                seconds = float((frame.pts - (stream.start_time or 0)) * stream.time_base)
                if seconds >= config["duration_seconds"]:
                    break
                decoded += 1
                if seconds + 1e-9 >= next_sample:
                    processed += 1
                    next_sample += 1 / config["sample_fps"]
                for sample, crop in by_pts.get(frame.pts, []):
                    x, y, x2, y2 = sample["plate_box"]
                    assert np.array_equal(frame.to_ndarray(format="bgr24")[y:y2, x:x2], crop)
                    assert abs(seconds - sample["relative_seconds"]) < 1e-9
                    checked += 1
        assert checked == reproductions
        return {
            "audited_worktree_base_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "audit_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "policy": config["policy"],
            "stored_progress": state["progress"],
            "predicted_passages": len(predictions),
            "outcomes": dict(Counter(p["observation"]["status"] for p in predictions)),
            "passages_with_plate_detections": sum(
                bool(p["inference"]["samples"]) for p in predictions
            ),
            "evidence_digests_verified": len(assets),
            "source_crop_checks": checked,
            "ocr_reproductions": reproductions,
            "consensus_reproductions": len(predictions),
            "decoded_recount": decoded,
            "scheduled_frame_recount": processed,
            "accuracy": "not measured by reproduction; independent labels required",
            "details": details,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "details"}))


if __name__ == "__main__":
    main()
