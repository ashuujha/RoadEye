import re
from collections import defaultdict

from roadeye.contracts import Reading

POLICY = "consensus-v1"
# Conventional illustrative AA00AA0000 shape only. This is not registration validation.
FORMAT = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$")


def normalize(raw: str) -> list[str]:
    text = re.sub(r"[\s-]", "", raw.upper())
    if FORMAT.fullmatch(text):
        return [text]
    if len(text) != 10 or not text.isascii() or not text.isalnum():
        return []
    result = list(text)
    for i, char in enumerate(text):
        digits = i in (2, 3, 6, 7, 8, 9)
        conversions = {"O": "0", "I": "1"} if digits else {"0": "O", "1": "I"}
        result[i] = conversions.get(char, char)
    candidate = "".join(result)
    return [candidate] if FORMAT.fullmatch(candidate) else []


def consensus(
    readings: list[Reading],
    quality: float,
    confidence: float,
    threshold: float = 0.8,
    margin: float = 0.2,
) -> dict:
    # Per-frame maximum per candidate: repeated frames never create extra votes.
    frames: dict[str, dict[str, float]] = defaultdict(dict)
    contributions = []
    for reading in readings:
        for candidate in reading.candidates:
            alternatives = normalize(candidate.text)
            contributions.append(
                {
                    "frame_id": reading.frame_id,
                    "raw": candidate.text,
                    "normalized": alternatives,
                    "input_score": candidate.confidence,
                }
            )
            for plate in alternatives:
                weight = candidate.confidence * quality * confidence
                frames[reading.frame_id][plate] = max(
                    frames[reading.frame_id].get(plate, 0), weight
                )
        frames[reading.frame_id]  # Unreadable frames still contribute to denominator.
    scores: dict[str, float] = defaultdict(float)
    for frame in frames.values():
        for plate, weight in frame.items():
            scores[plate] += weight / max(1, len(frames))
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best = ranked[0][1] if ranked else 0
    gap = best - (ranked[1][1] if len(ranked) > 1 else 0)
    if not ranked:
        status, reasons = "rejected", ["NO_SUPPORTED_CANDIDATE"]
    elif best + 1e-12 >= threshold and gap + 1e-12 >= margin:
        status, reasons = "accepted", ["CONSENSUS_ACCEPTED"]
    else:
        status, reasons = "review_required", ["LOW_SCORE" if best < threshold else "SMALL_MARGIN"]
    return {
        "plate": ranked[0][0] if ranked else None,
        "status": status,
        "reasons": reasons,
        "score": best,
        "margin": gap,
        "alternatives": [{"plate": p, "score": s} for p, s in ranked],
        "contributions": contributions,
        "independent_frames": len(frames),
        "policy": POLICY,
        "thresholds": {"accept": threshold, "margin": margin},
        "score_meaning": "provisional heuristic, not calibrated probability",
    }
