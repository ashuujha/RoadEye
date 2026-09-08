# Returned Re-ID model and frozen S02 audit — hours 24–27

## Completed

- Validated the returned ZIP, its exact model/config/bundle hashes, all 16 history rows, epoch selection, and local Python 3.11 CPU inference.
- Added trained-model provenance enforcement to the existing runtime without exposing training identities or associations.
- Froze the accepted weights, runtime sources, unchanged association policy, and the first 180 seconds of all four S02 cameras before opening S02 GT.
- Ran one causal CPU prediction, deterministic replay, separate evaluation, integrity audit, and error analysis. No frontend, OCR, analytics, or API work started.

## Verified

- **PASS — returned artifact:** ZIP SHA-256 `2d8b0992b30348ad4be99f35edebce38043365da5d7b2038307209a5765584d4`; model SHA-256 `1a7bddc94b065da1cc76f27f3455d61dc9752e687a87101c2eeb566353185cac`; safe members and CRC passed. Best epoch recomputes to 7.
- **PASS — development improvement:** rank-1 increased from 67/99 (67.68%) to 87/99 (87.88%), +20.20 percentage points. mAP increased from 0.5732 to 0.8829, +0.3097. These are identity-camera pooled S01/S03 development metrics.
- **PASS — CPU runtime:** exact-hash model loads frozen on Python 3.11.9, torch 2.4.1+cpu and emits a finite `[1, 2048]` descriptor.
- **PASS — S02 isolation:** training scenarios are S01/S03, `evaluation_scenarios_used` is empty, and S02 model/window/policy/source hashes were frozen before scoring.
- **PASS — runtime integrity:** cached inference accesses neither GT nor network; prediction hashes repeat; all 4,620 crop hashes pass; 37/37 links use evidence available by decision time; three CPU re-embeddings have maximum absolute error 0.0.

## Measured S02 results

- Scope: four cameras, first 180 seconds; 1,671 baseline tracklets and 118,794 observations.
- Embedded/assigned: 1,540 tracklets from 4,620 crops; 131 tracklets lacked a complete three-observation prefix.
- Predictions: 37 links, 1,503 RoadEye global IDs, three-camera predicted maximum.
- GT mapping: 87 matched, 245 ambiguous, and 1,339 unmatched baseline tracklets. Visit coverage is 85/423 (20.09%).
- Link evidence: 3 correct, 0 incorrect, 34 unscored. Precision on evaluable links is 3/3 (100%); evaluation coverage is 3/37 (8.11%). The all-link precision range is 8.11%–100% because unknown links are not assumed correct or incorrect.
- Global-ID pairs: precision 3/3 (100%); recall 3/23 (13.04%), including the all-mappable denominator.
- Causal retrieval: 10/20 rank-1 (50.0%), mAP 0.6170.
- Longest fully scored consistent journey: two cameras. S02 has only four cameras and cannot verify the six-camera criterion.
- CPU timing: crop extraction 150.87 seconds, embedding 1,024.09 seconds, association 5.68 seconds.

## Unverified

- **UNVERIFIED:** 34/37 predicted links have insufficient released-label mapping and remain unknown.
- **UNVERIFIED:** the returned manifest does not cryptographically link the exact training code ZIP, although its bundle/config/model hashes and output schema match the supplied job.
- **UNVERIFIED:** upstream MTSC training provenance and causality remain outside RoadEye's audit.
- **UNVERIFIED:** performance on a city-wide population or an official hidden benchmark is not measured.

## Failed

- **FAIL — six-camera goal:** the fully scored consistent maximum is two cameras; the predicted three-camera group is not verified.
- **FAIL — recall:** pairwise recall is 3/23 (13.04%), despite perfect precision on only three evaluable predicted pairs.
- **FAIL — documented training environment:** Colab ran Python 3.13.15, torch 2.11.0+cu128, and torchvision 0.26.0+cu128 instead of the documented Python 3.11/torch 2.4 environment. Local Python 3.11 CPU compatibility passes.

## Highest-impact improvement

Nineteen of 20 labelled causal queries retain a positive after temporal/topology gates, but only three have a positive above the fixed 0.85 similarity threshold. Calibrate similarity and ambiguity rejection using S01/S03 development identities only, then use S05 solely as a disclosed post-hoc demo comparison. S02 is consumed and must not select or validate new parameters. Stop at this audit and local commit before starting that repair or the hours 27–33 frontend phase.

## Tests and changed files

- `python -m pytest -q`: 42 passed.
- Ruff format/check: passed for source, relevant scripts, tests, and notebook.
- `python -m pip check`: no broken requirements.
- All 30 config/report/notebook JSON documents parsed; the frozen config, copied metrics, and integrity result cross-check passed.
- Runtime changes: `src/roadeye/phase2.py`; generic window-freezing extension: `scripts/freeze_reid_windows.py`; returned-artifact and selection tools: `scripts/verify_reid_result.py`, `scripts/freeze_trained_reid_selection.py`; trained-model/S02 configs, reports, engineering documents, and policy tests. Raw data, crops, returned weights, and generated databases remain ignored.
