"""CPU ONNX adapters. Model inputs/outputs are checked; downloads never occur here."""

import json
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]

from roadeye.evidence import digest

MODEL_MANIFEST = Path(__file__).with_name("models.json")
POLICY = "recorded-onnx-v1"


def verify_models(root: Path) -> dict:
    manifest = json.loads(MODEL_MANIFEST.read_text())
    for name, entry in manifest.items():
        path = root / f"{name}.onnx"
        if not path.is_file():
            raise ValueError(f"MODEL_UNAVAILABLE: {name}; run scripts.download_models")
        if digest(path.read_bytes()) != entry["sha256"]:
            raise ValueError(f"MODEL_DIGEST_MISMATCH: {name}")
    return manifest


class Detector:
    """YOLO11 RGB letterbox / float32 [0,1], NMS and original-pixel boxes."""

    def __init__(self, root: Path, kind: str):
        self.kind = kind
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(root / f"{kind}.onnx"), options, providers=["CPUExecutionProvider"]
        )

    def detect(self, image, threshold: float = 0.3) -> list[dict]:
        h, w = image.shape[:2]
        scale = min(640 / w, 640 / h)
        nw, nh = round(w * scale), round(h * scale)
        left, top = (640 - nw) // 2, (640 - nh) // 2
        canvas = np.full((640, 640, 3), 114, np.uint8)
        canvas[top : top + nh, left : left + nw] = cv2.resize(image, (nw, nh))
        tensor = canvas[:, :, ::-1].transpose(2, 0, 1)[None].astype("float32") / 255
        out = self.session.run(None, {"images": tensor})
        if self.kind == "plate":
            raw = out[0][0].T
            boxes = raw[:, :4].copy()
            boxes[:, :2] -= boxes[:, 2:] / 2
            scores = raw[:, 4]
            classes: np.ndarray = np.zeros(len(raw), int)
        else:
            # Espressif's documented export exposes DFL distance logits and class logits.
            all_boxes, all_scores, all_classes = [], [], []
            for level, stride in enumerate((8, 16, 32)):
                logits = out[2 * level][0].reshape(4, 16, -1)
                logits -= logits.max(1, keepdims=True)
                probabilities = np.exp(logits)
                probabilities /= probabilities.sum(1, keepdims=True)
                distances = (probabilities * np.arange(16)[None, :, None]).sum(1)
                yy, xx = np.mgrid[: 640 // stride, : 640 // stride]
                xy = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5])
                boxes_level = (
                    np.concatenate([xy - distances[:2], distances[:2] + distances[2:]], axis=0).T
                    * stride
                )
                score_matrix = 1 / (1 + np.exp(-out[2 * level + 1][0].reshape(80, -1)))
                cls, score = score_matrix.argmax(0), score_matrix.max(0)
                score[~np.isin(cls, [2, 3, 5, 7])] = 0  # car, motorcycle, bus, truck
                all_boxes.append(boxes_level)
                all_scores.append(score)
                all_classes.append(cls)
            boxes, scores, classes = map(np.concatenate, (all_boxes, all_scores, all_classes))
        indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), threshold, 0.45)
        result = []
        for i in indices:
            x, y, bw, bh = boxes[i]
            box = [
                max(0, int((x - left) / scale)),
                max(0, int((y - top) / scale)),
                min(w, int((x + bw - left) / scale)),
                min(h, int((y + bh - top) / scale)),
            ]
            if box[2] > box[0] and box[3] > box[1]:
                result.append({"box": box, "score": float(scores[i]), "class": int(classes[i])})
        return sorted(result, key=lambda d: tuple(d["box"]))


class Recognizer:
    """Physical crop only: upstream RGB uint8, bilinear resize 128×64, ten slots."""

    def __init__(self, root: Path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(
            str(root / "ocr.onnx"), options, providers=["CPUExecutionProvider"]
        )

    def recognize(self, crop) -> dict:
        if crop.size == 0:
            raise ValueError("EMPTY_PHYSICAL_PLATE_CROP")
        rgb = cv2.resize(crop[:, :, ::-1], (128, 64), interpolation=cv2.INTER_LINEAR)
        output = self.session.run(["plate"], {"input": rgb[None]})[0][0]
        indices = output.argmax(1)
        raw = "".join("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"[i] for i in indices)
        scores = output.max(1)
        used = [float(score) for char, score in zip(raw, scores, strict=True) if char != "_"]
        return {
            "raw_slots": raw,
            "text": raw.replace("_", ""),
            "confidence": sum(used) / len(used) if used else 0,
            "character_scores": scores.tolist(),
            "preprocessing": "physical BGR crop → RGB uint8 → bilinear 128x64; no enhancement",
            "model": "cct-xs-v2-global",
            "score_meaning": "uncalibrated model score",
        }


def iou(a, b) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union else 0


class Tracker:
    """Deterministic local IoU association; counts downward bottom-centre crossings once.

    Not re-identification. Occlusion/fragmentation can miss or duplicate physical vehicles.
    """

    def __init__(self, line_y: int = 300):
        self.tracks: dict[str, dict] = {}
        self.next_id = 1
        self.line_y = line_y

    def update(self, detections: list[dict], seconds: float, pts: int):
        active = [t for t in self.tracks.values() if seconds - t["last_seen"] <= 1]
        pairs = sorted(
            (
                (-iou(t["box"], d["box"]), t["id"], j)
                for t in active
                for j, d in enumerate(detections)
            )
        )
        matched_tracks, matched_detections = set(), set()
        assignments = []
        for neg_score, identity, index in pairs:
            if -neg_score < 0.15 or identity in matched_tracks or index in matched_detections:
                continue
            matched_tracks.add(identity)
            matched_detections.add(index)
            assignments.append((self.tracks[identity], detections[index]))
        for j, detection in enumerate(detections):
            if j not in matched_detections:
                identity = f"track-{pts}-{self.next_id}"
                self.next_id += 1
                track = {
                    "id": identity,
                    "box": detection["box"],
                    "last_seen": seconds,
                    "hits": 0,
                    "crossed": False,
                    "samples": [],
                    "crossing": None,
                }
                self.tracks[identity] = track
                assignments.append((track, detection))
        for track, detection in assignments:
            previous = track["box"][3]
            track.update(box=detection["box"], last_seen=seconds, hits=track["hits"] + 1)
            if (
                not track["crossed"]
                and track["hits"] >= 2
                and previous < self.line_y <= track["box"][3]
            ):
                track["crossed"] = True
                track["crossing"] = {"seconds": seconds, "pts": pts, "vehicle": detection}
        expired = [t for t in self.tracks.values() if seconds - t["last_seen"] > 1]
        for track in expired:
            del self.tracks[track["id"]]
        return assignments, expired
