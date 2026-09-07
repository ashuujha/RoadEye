# Phase 2 foundation repair audit — 2026-09-07

Checkpoint: repair of the approved Phase 2 (planned hours 10–18). The inference/evaluation foundation is implemented and verified; the six-camera predicted-journey demo is **not achieved**. No later phase has started.

## Completed

- Reused the existing CityFlow dataset, S04 frozen window, and DeepSORT/Mask R-CNN predicted local tracklets. Removed the camera-order cap of 30; all 25 configured cameras are inspected.
- Replaced HSV-only features with the architecture's generic ImageNet ResNet-50 CPU fallback. Extracted first-three-observation prefixes in one sequential video pass per camera; cached crops, aligned embeddings, model provenance, and input hashes.
- Moved GT reads entirely into a separately invoked evaluator. Runtime tracklet/evidence schemas contain no identity annotations. Removed the hardcoded runtime-GT claim.
- Implemented chronological decisions using only observed prefixes, conservative calibration-proximity/time constraints, independent UUID-based global IDs, ambiguity rejection, and explainable accepted/rejected candidates.
- Produced assignments, accepted links, decision records, and chronological observation journeys with evidence and approximate geographic provenance. No API, frontend, OCR, streaming infrastructure, or road-matching implementation was added.
- Corrected evaluation to use one-to-one per-frame IoU matching with coverage and identity-purity requirements. Missing labels remain unscored and no evaluable links yield null, not 0% accuracy.
- Added run instructions, claim corrections, an actual integrity audit, and repo-local pytest temporary storage. Existing raw datasets and the old run artifacts are preserved and ignored by Git.

## Verified measurements

The fixed diagnostic window is S04, scenario-relative seconds **10.1–204.044**. The window was selected with GT coverage during feasibility and is not an unbiased held-out benchmark. Parameters were fixed before this repaired run; no CityFlow model training or S04 threshold tuning was performed. S01/S03 are reserved for later development.

| Measurement | Actual result |
|---|---:|
| Cameras in the input window | 25 |
| Baseline observations | 137,687 |
| Baseline tracklets | 1,723 |
| Embedded and assigned tracklets | 1,573 |
| Excluded tracklets with fewer than three observations | 150 |
| Extracted prefix crops | 4,719 |
| Embedding dimensions | 2,048 |
| Independent predicted global IDs | 1,513 |
| Accepted cross-camera links | 60 |
| Evaluable links | 10 |
| Correct / incorrect evaluable links | 6 / 4 |
| Unscored links | 50 |
| Precision on evaluable links | **60% (6/10)** |
| Fraction of all links evaluable | **16.67% (10/60)** |
| Global-ID pairwise precision on scored tracklets | 60% (6/10) |
| Global-ID pairwise recall on scored tracklets | **1.38% (6/435)** |
| Causal appearance retrieval Rank-1 | 16.89% (25/148 queries) |
| Causal appearance retrieval mAP | 16.35% (148 queries) |
| GT camera visits represented by scored assigned tracklets | 66.13% (205/310) |
| Longest predicted group | 4 cameras |
| Longest fully scored, GT-consistent group under the mapping protocol | **2 cameras** |

The 60% figure applies only to ten scored links; it is **not** overall tracking accuracy. Fifty links cannot be adjudicated by the available mappings. Possible full-link precision bounds under those unknown outcomes are 10%–93.33%, not a confidence interval. No accuracy or generalization claim is inferred from that wide range.

GT mapping counts: **218 matched**, **118 ambiguous**, **1,387 unmatched** baseline tracklets. The evaluator inspected **22,770 GT rows** in this window. Unmatched baseline tracklets are not automatically false positives: CityFlow labels only a subset of traffic. Four predicted groups contain conflicting scored GT identities; 13 are partially scored, 1,305 unscored, and 191 fully scored/consistent (mostly single-camera).

Decision counts: 19 new IDs had no eligible temporal/topology candidate; 1,211 were below the fixed appearance threshold; 283 were rejected by the ambiguity margin; 60 were linked. This is an initial conservative association policy, not a calibrated model.

## Runtime and checks

Machine: Intel Core i5-1235U; inference restricted to CPU. Actual versions: Python 3.11.9, Torch 2.4.1+cpu, torchvision 0.19.1+cpu, OpenCV 4.11.0, NumPy 1.26.4, SciPy 1.17.1, Pillow 12.3.0. `pip check` found no broken requirements. Existing dependency installation was reused.

- Sequential crop extraction: **159.91 seconds**.
- CPU feature extraction: **375.39 seconds** for 4,719 crops, including model setup/preprocessing.
- Association over cached evidence: **6.00 seconds** on the first run, **5.19 seconds** on the verification repeat. This excludes preparation and is not a streaming FPS claim.
- Tests: **23 passed**. Tests cover first-prefix availability, extension of future tracks, topology/time rejection, overlap allowance, ambiguity, independent IDs, same-camera transitive merge prevention, GT isolation, box clipping, IoU matching uniqueness, mixed-identity rejection, unknown metrics, split separation, input hashes, and tampered predictions.
- Ruff and `git diff --check`: passed.
- Real cached inference ran with GT-file access and socket connections forbidden. Prediction hashes were identical on repeat.
- Real-data prefix invariance passed at 50, 100, and 150 seconds: **120, 400, and 902 earlier decisions** respectively were unchanged when future observations were removed.
- All **60 accepted links** passed evidence-time checks: no appearance sample or source observation came after its recorded decision.

The first test run had 16 passing tests and three fixture errors because the system pytest temporary directory denied access. Configuring `.pytest_cache/tmp` fixed that environment issue; all final tests passed. No data or unrelated processes were deleted/stopped during this repair.

## Failed, unverified, and deferred

- **FAIL — six-camera predicted journey:** only two cameras are supported by the longest fully scored consistent group. Ground-truth availability across 24 cameras does not mean the model reconstructs that journey.
- **FAIL — useful association recall:** scored pairwise recall is 1.38%; four of ten scored direct links are wrong. This is not ready to present as a reliable city-wide tracker.
- **UNVERIFIED — 50 links:** partial/ambiguous labels prevent judging these links. They are neither counted as correct nor silently called incorrect.
- **UNVERIFIED — generalization:** this GT-selected S04 diagnostic, with a labeled-only retrieval gallery, is not the official hidden test or an unbiased holdout.
- **UNVERIFIED — upstream MTSC causality/training provenance:** the provided baseline tracks are used as inputs. RoadEye's own causal processing is tested; the upstream implementation has not been independently audited.
- **UNVERIFIED — exact GPS/topology:** inverse-calibrated ROI points are approximate road-plane references; proximity is not verified road connectivity or exact camera location.
- Indian OCR/transcription, vehicle-specific Re-ID training/export, a fresh evaluation slice, UI/API, and later analytics remain deferred.

## Deviations and corrections

The earlier assertion that Phase 2 had valid 0% precision is withdrawn: zero GT coverage made quality unverified. The earlier loader also carried GT identity fields into runtime and used future whole-track information for early decisions. Those foundation issues are repaired here.

The repair completes the generic ResNet fallback instead of the previous HSV-only shortcut. A vehicle-specialized checkpoint/export remains deferred to an explicitly approved improvement phase. The first-three-prefix policy prioritizes causal evidence over full-track averaging; it may include tiny, edge-clipped, or low-quality early crops. Calibration-based proximity constraints were added because no prior concrete topology graph existed. Exact camera GPS is not supplied by the dataset, contrary to the earlier planning assumption.

The existing four planning documents were already abbreviated relative to the originally approved proposal. This checkpoint corrects Phase 2-specific architecture and claims; it does not reconstruct unrelated planning sections or restart the project.

## Highest-impact next work — recommendation only

First improve appearance discrimination on a development split using a vehicle-specialized Re-ID model and causally accumulated, quality-filtered crop prefixes. The generic model's 25/148 Rank-1 retrieval result shows an appearance bottleneck independent of the conservative linking threshold. Inspection of scored errors also shows similar-looking vehicles and very small crops. Lowering the link threshold alone would not establish reliable identity matching.

Use S01/S03 for development and freeze a fresh evaluation slice before any tuning. Keep this S04 report unchanged as the current diagnostic. Plan that bounded improvement checkpoint before claiming a six-camera demo; the phase at hours 18–24 can then consume the existing evidence/journey artifacts. Neither improvement work nor the frontend phase has started.

## Files and local checkpoint

- Runtime: `src/roadeye/phase2.py`, `tracklets.py`, `embeddings.py`, `association.py`, and package description.
- Evaluation: `src/roadeye/evaluation.py`.
- Commands/tests: `scripts/run_phase2.py`, `scripts/verify_phase2.py`, `tests/test_phase2.py`.
- Reproducibility: `configs/phase2.json`, the existing `configs/feasibility-window.json` added to version control, `.gitignore`, `pyproject.toml`, and direct-dependency pins in `requirements-cpu.txt`.
- Documentation: `prd.md`, `architecture.md`, `plan.md`, this audit, `phase2-runbook.md`, `phase2-metrics.json`, and `phase2-integrity.json`.

The pre-existing untracked `scripts/feasibility_cityflow.py` is preserved unchanged. Raw data, images, model weights, runtime/evaluation artifacts, and the old environment log remain outside Git. No remote is configured or pushed. The containing local commit is the Phase 2 repair checkpoint; its hash is reported in the user handoff.
