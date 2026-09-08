"""Causal appearance descriptor fusion for development-calibrated association."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import cv2
import numpy as np

from .tracklets import sha256


def _unit(vector: np.ndarray, label: str) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if not np.isfinite(value).all() or norm <= 0:
        raise ValueError(f"Invalid {label} descriptor")
    return value / norm


def hsv_histogram(image: np.ndarray, bins: tuple[int, int, int]) -> np.ndarray:
    """Return a normalized HSV histogram from one already-arrived vehicle crop."""

    if image is None or image.size == 0 or len(bins) != 3 or min(bins) < 1:
        raise ValueError("Invalid crop or HSV histogram bins")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist(
        [hsv], [0, 1, 2], None, list(bins), [0, 180, 0, 256, 0, 256]
    ).reshape(-1)
    return _unit(histogram, "HSV")


def tracklet_hsv_descriptors(
    output: Path, metadata: dict, bins: tuple[int, int, int]
) -> dict[str, np.ndarray]:
    """Pool only the hash-bound prefix crops already used by the Re-ID encoder."""

    descriptors = {}
    for key, tracklet in metadata.items():
        samples = tracklet.get("samples", [])
        if not samples:
            raise ValueError(f"No appearance evidence samples: {key}")
        vectors = []
        for sample in samples:
            crop = output / sample["crop"]
            if sha256(crop) != sample["crop_sha256"]:
                raise ValueError(f"Appearance crop hash mismatch: {key}")
            image = cv2.imread(str(crop), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"Unreadable appearance crop: {crop}")
            vectors.append(hsv_histogram(image, bins))
        descriptors[key] = _unit(np.mean(vectors, axis=0), "pooled HSV")
    return descriptors


def fuse_descriptors(
    reid: dict[str, np.ndarray], hsv: dict[str, np.ndarray], hsv_weight: float
) -> dict[str, np.ndarray]:
    """Concatenate unit descriptors so cosine is their declared weighted sum."""

    if set(reid) != set(hsv):
        raise ValueError("Re-ID and HSV descriptor keys differ")
    if not 0 <= hsv_weight <= 1:
        raise ValueError("HSV weight must be between zero and one")
    reid_scale = math.sqrt(1.0 - hsv_weight)
    hsv_scale = math.sqrt(hsv_weight)
    return {
        key: _unit(
            np.concatenate(
                (
                    _unit(reid[key], "Re-ID") * reid_scale,
                    _unit(hsv[key], "HSV") * hsv_scale,
                )
            ),
            "fused",
        )
        for key in sorted(reid)
    }


def add_link_similarity_evidence(
    predictions: dict,
    reid: dict[str, np.ndarray],
    hsv: dict[str, np.ndarray],
    hsv_weight: float,
    crop_artifact_root: str,
) -> dict:
    """Explain every accepted fused score without changing any association."""

    result = copy.deepcopy(predictions)

    def evidence(source: str, target: str, combined: float) -> dict:
        reid_similarity = float(np.clip(np.dot(reid[source], reid[target]), -1, 1))
        hsv_similarity = float(np.clip(np.dot(hsv[source], hsv[target]), -1, 1))
        reconstructed = (1.0 - hsv_weight) * reid_similarity + hsv_weight * hsv_similarity
        if abs(combined - reconstructed) > 2e-5:
            raise ValueError("Fused score does not match its evidence components")
        return {
            "descriptor": "weighted_concatenation_of_unit_reid_and_causal_hsv_prefix",
            "reid_cosine_similarity": reid_similarity,
            "hsv_cosine_similarity": hsv_similarity,
            "hsv_weight": hsv_weight,
            "reid_weight": 1.0 - hsv_weight,
            "reconstructed_similarity": reconstructed,
            "crop_artifact_root": crop_artifact_root,
            "score_kind": "development_selected_similarity_not_probability",
        }

    for link in result["links"]:
        link["appearance_evidence"] = evidence(
            link["from_key"], link["to_key"], link["similarity"]
        )
    for decision in result["decisions"]:
        for candidate in decision["top_candidates"]:
            candidate["appearance_evidence"] = evidence(
                candidate["from_key"], decision["key"], candidate["similarity"]
            )
    return result
