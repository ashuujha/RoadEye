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

The frozen S05 evaluation did not meet the core journey criterion. It measured
2/4 correct evaluable links, 2/647 pairwise recall, and a longest fully scored
consistent journey of two cameras. The data/mapping contains ten identities
across at least six cameras, so the shortfall is the current association system.
The three-camera predicted maximum is not a verified success. These measured
numbers replace any implication that the bounded pretrained-model experiment
established a six-camera demo.

The approved training-only repair uses CityFlow training scenarios S01/S03 and
an identity-disjoint development split. S02/S04/S05 identities, associations, and
future observations are excluded from training and model selection. Development
rank-1 and mAP are model-selection measurements only. A fine-tuned model may be
called an improvement only if the recorded development result exceeds its
epoch-zero baseline; neither result is city-wide or held-out test accuracy.
The runtime receives only the exported encoder and its provenance manifest,
never training identities or associations. Until the private GPU job runs and
the returned artifact passes local CPU verification, fine-tuned performance is
**UNVERIFIED**.

The returned model measured 87/99 rank-1 and 0.8829 mAP on its identity-disjoint
S01/S03 development pools, versus 67/99 and 0.5732 at epoch zero. On the one
frozen S02 run, only 3/37 predicted links were evaluable; all three were correct,
while 34 remain unknown. Pairwise recall was 3/23, causal retrieval rank-1 was
10/20, and the longest fully scored consistent journey covered two cameras.
S02 contains four cameras, so it cannot verify the six-camera demo criterion.
These are exact local-slice measurements with small/partial denominators, not
city-wide or official benchmark accuracy. S02 is now consumed for model
comparison and cannot be reused as a fresh evaluation after tuning.

The hours 27–33 local interface now renders all 35 frozen S02 multi-camera
predictions, with crop selection, boxed source frames, approximate camera points,
chronological replay, and 37 link-evidence records. This is a delivery result, not
an accuracy improvement. Its strongest displayed prediction spans three cameras;
the verified maximum remains two cameras. Plate-string search and analytics remain
unimplemented until their independent phases.
