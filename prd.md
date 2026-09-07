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

