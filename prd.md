# Product Requirements Document — BEL City-Wide ANPR Trajectory Demo

## Problem
City cameras operate in isolation. This demonstrator links real multi-camera vehicle observations, shows a selected journey in time order, and summarizes observed traffic movement.

## In scope
- CityFlow-V2 real cross-camera data, primarily appearance re-identification with OCR as a secondary signal.
- Indian plate benchmark for independently measured detection and full-string OCR.
- CPU local inference and a minimal test frontend: crop selection, plate search, evidence frames, map trajectory, replay, density, OD, and bottleneck proxies.
- Straight-line interpolation between known camera GPS points, explicitly labeled as inferred geometry.
- Reproducible held-out evaluation and portable optional Colab artifacts.

## Out of scope
Kafka/streaming ingestion, full road-network map matching, production deployment, access-control/retention enforcement, ownership lookup, facial identification, unrestricted uploads, and any frontend outside `test_frontend/`. These do not protect the two-day-class demo and require production governance or infrastructure.

## Demo success criteria
A real selected crop produces a predicted journey across the best verified set of CityFlow cameras, chronologically, with source frame, timestamp, camera, and score for every observation. Ambiguous matches remain unresolved. The demo runs locally on CPU with cached assets and no hidden downloads.

## Claims and evaluation
The stated 90%+ plate accuracy is a target only. Report exact full-string accuracy, detection precision/recall, character error rate, confidence intervals, denominators, unreadable cases, and CPU latency on a frozen independent test split. If 150–300 independent test images are unavailable, report the actual smaller number. CityFlow results are local held-out retrieval/link metrics against released identities, never a hidden-test or city-wide claim. Scores are uncalibrated confidence/similarity values, not probabilities.

## Data decision
CityFlow plates are not reliable Indian OCR evidence; therefore cross-camera identity is appearance-led and OCR is optional secondary evidence. Indian OCR is evaluated on a separate real Indian dataset. No labels or fabricated plates are used at runtime.

## Current claim corrections

The initial 30-tracklet Phase 2 run had zero matched GT tracklets. Its recorded `link_precision: 0.0` is invalid as an accuracy result; quality was unverified. The repaired evaluator must report null when no links are evaluable, and report unscored links separately from known incorrect links.

The frozen S04 window was selected with GT camera coverage during feasibility. Results on it must be described as a fixed diagnostic subset, with no claim of unbiased held-out generalization. No CityFlow training or S04 threshold tuning is allowed in the repaired run. The originally requested six-camera demonstration is achieved only by predicted associations that can be checked against actual evidence; six-camera GT availability alone does not establish that success.

The supplied data has approximate scenario GPS centers and calibration matrices, not exact surveyed camera GPS locations. Calibration-derived map positions must retain their approximate provenance. Indian ANPR remains separate and does not block the user-approved Phase 2 repair.

The bounded Re-ID extension compares a VeRi-trained encoder and causal crop
quality filtering on S01 development data. Its S05 evaluation is separate from
parameter selection but shares locations with the previously inspected S04
diagnostic; it is not an official benchmark or a novel-site generalization claim.
Report unknown links, crop exclusions and partial-label coverage alongside every
accuracy result. Pairwise recall over all mappable baseline tracks accompanies
recall conditional on successfully embedded tracks. A six-camera prediction is
not a verified journey unless every member is scored consistently against the
released labels under the documented matching protocol.
