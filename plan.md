# 56-hour build plan (four calendar days / 96 elapsed hours)

| Hours | Work | Priority |
|---|---|---|
| 0–2 | Planning and feasibility protocol | Critical |
| 2–10 | Python 3.11 setup; CityFlow and Indian downloads/audit; freeze feasible subsets; evidence report | **Critical gate** |
| 10–18 | CityFlow import, CPU embeddings, association baseline, evaluator | Critical |
| 18–21 | Bounded pretrained vehicle Re-ID comparison and frozen evaluation | Critical repair; completed |
| 21–24 | Private S01/S03 training bundle, portable Colab job, and CPU artifact contract | Critical repair; approved checkpoint |
| 24–27 | Returned-model acceptance and one frozen S02 evaluation | Critical repair; completed |
| 27–33 | Crop selection, evidence timeline, map, and replay | Critical; completed |
| 33–43 | Indian transcription/review, detector/OCR, preprocessing, and evaluation | Critical |
| 43–47 | Plate search, hybrid evidence, OD, density heat map, and bottleneck proxies | Required |
| 47–52 | Remaining frozen evaluation, leakage checks, error analysis, and CPU timing | Critical |
| 52–56 | Integration repair, offline rehearsal, claims, and evidence packaging | Critical |

Hard gates remain unchanged: verify actual CityFlow camera coverage and Indian transcription/test capacity before implementation; never use ground truth at runtime or fabricate journeys. Allow up to one hour for Roboflow/IEEE checks and six hours for transcription review. Cut extra model variants, supplementary datasets, further tuning, and presentation polish first. Never cut evaluation, provenance, uncertainty, or CPU rehearsal.

## Completed Phase 2 repair, hours 10–18

The repaired command processes the full frozen S04 window, isolates ground truth, makes causal decisions, and emits measured diagnostic results. The S04 window was selected with identity coverage during feasibility and is a diagnostic subset. See `reports/phase2-audit.md` and `reports/phase2-metrics.json`.

## Completed bounded Re-ID comparison, hours 18–21

The VeRi encoder passed exact CPU adapter parity and improved S01 labelled-gallery retrieval, but none of 30 predeclared development configurations met the minimum evidence/precision gate. The frozen fallback retained the original ImageNet model and thresholds for one S05 evaluation. S05 measured 2/4 correct evaluable links, 2/647 pairwise recall, and a longest fully scored consistent journey of two cameras. Ten S05 identities are mappable across at least six cameras, so the current system does not meet the six-camera criterion. S05 is consumed and cannot become a fresh test through retuning. See `reports/reid-audit.md`.

## Approved training-only checkpoint, hours 21–24

Move the three-hour portable setup allocation ahead of frontend work without changing the 56-hour total. Build a private, derived crop bundle from training scenarios S01/S03 only. Split by scoped identity before crop extraction, use no S02/S04/S05 labels, and select the best epoch using development identity-camera pooled cross-camera mAP, with rank-1 and earlier epoch as tie-breakers. Record the unfine-tuned epoch-zero baseline so a trained result cannot be called an improvement without evidence. Preserve validation scenario S02 for one separately approved frozen evaluation after model selection.

The portable job uses the official exact-hash VeRi checkpoint for initialization, cross-entropy plus batch-hard triplet loss, and a CUDA runtime only for training. It exports a versioned exact-hash encoder that the existing demo loads on CPU. The local bundle/job construction and export/import contract are part of this checkpoint. Training metrics and the returned trained artifact remain **UNVERIFIED** until the user privately runs the Colab notebook and returns its result ZIP. No frontend, OCR, analytics, or additional evaluation begins before the checkpoint audit and explicit clearance.

### Hours 21–24 measured construction result

The private ignored bundle contains 2,900 real S01/S03 crops across 11 cameras and 113 multi-camera identities: 2,318 crops/90 identities for training and 582 crops/23 identities for development, with zero identity overlap and zero crop exclusions. Archive integrity and every crop hash passed. The code-only Colab archive contains no data, weights, or credentials and passed its internal source-hash verification. A real 2048-dimensional encoder export reloaded on local CPU with exact tensor equality and zero maximum difference. These are construction and portability checks, not Re-ID accuracy results.

## Completed returned-model evaluation, hours 24–27

The returned epoch-7 encoder improved identity-disjoint S01/S03 development retrieval from 67/99 to 87/99 rank-1 and from 0.5732 to 0.8829 mAP. The exact weight hash loaded on Python 3.11 CPU. The result manifest nevertheless has two recorded limitations: Colab used Python 3.13/torch 2.11 rather than the documented training versions, and it did not cryptographically link the job code archive.

Model, unchanged association thresholds, S02 metadata window, provenance, weights, and runtime source hashes were frozen before identity scoring. The one S02 run measured 3/3 correct evaluable links, 3/23 pairwise recall, 10/20 causal retrieval rank-1, and 0.6170 retrieval mAP. Only 3/37 links were evaluable, 34 remain unknown, and the longest fully scored journey spans two cameras. S02 has four cameras and cannot establish a six-camera result. S02 is now consumed; future variants there are post-hoc only.

## Completed local evidence interface, hours 27–33

The prediction-only FastAPI service and `test_frontend/` now load the frozen S02
runtime artifacts after exact hash checks. They expose 1,503 RoadEye vehicle IDs,
35 multi-camera predictions and 37 predicted links without opening evaluator
identity mappings. The interface supports RoadEye-ID/tracklet/camera search, crop
selection, a chronological evidence timeline, locally decoded boxed source frames,
an offline Leaflet camera view, explicitly dashed straight-line interpolation, and
timed replay. Scores are labelled as uncalibrated values rather than probabilities.

The interface does not change the model result: the predicted maximum is three
cameras and the previously measured fully scored consistent maximum remains two.
Plate search and aggregate analytics remain in their later phases. See
`reports/frontend-audit.md`.
