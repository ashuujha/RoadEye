# Recognition investigation — SIH2026172

Audited **2026-09-05 UTC**, baseline commit **ce06494**, implementation checkpoint **13759e8**. This is a pipeline investigation, not a labelled recognition benchmark. Commands/results and blocked checks are recorded in [progress audit](progress_audit.md). Original run `fe25474a-fa66-404d-9213-7013e3ca687f` and separate v2 run `d7d83f8c-76ef-40fc-8c20-30c53f772ca9` remain in PostgreSQL. No real plate transcriptions are published here.

## Why only two accepted passages?

The original 25 predicted crossings split into three with no retained plate crop, fourteen with crops but **no supported normalized reading**, six with a supported candidate but insufficient consensus score, and two accepted. All six review decisions have `LOW_SCORE`; all seventeen rejections have `NO_SUPPORTED_CANDIDATE`. These are verified backend reasons, not human judgements about readability. The two accepted observations each used one retained OCR frame: “consensus accepted” does not guarantee multiple corroborating frames.

`consensus-v1` divides accumulated candidate weights by the number of distinct retained frames, including unsupported readings. Thus one ~0.995 candidate among two distinct frames produces ~0.498, below the unchanged 0.8 threshold. Retained frames are deduplicated by PTS/frame ID, but nearby frames remain correlated. The 0.2 margin and input quality/confidence multipliers (both neutral 1.0 for this adapter) are heuristic. There is no measured probability calibration.

## Evidence versus hypotheses

| Possible cause | Observed evidence | Conclusion / next discriminating check |
|---|---|---|
| Vehicle tracking mistakes | 5 FPS greedy IoU association; no appearance/motion model; one-second expiry. Passage IDs start with local track PTS. Full video review has not been labelled. | Counts could contain misses/fragmentation/duplicates. No defensible error count yet. Survey every downward crossing, including vehicles with no prediction. |
| Missing plate detections | No retained crops at crossing times 28.0, 38.4, 54.8 s in the original run. | This establishes absence of retained proposals, not that no plate was visible or no detector invocation ever proposed one. Review source/vehicle association before attributing cause. |
| Incorrect plate detection | Inspected crop around 34 s is apparently blank bodywork; OCR is empty. | A concrete visual false-proposal example, not an adjudicated dataset label or detector precision estimate. Human reviewer should classify it. |
| Source unreadability | Inspected nearby frames show variable perspective, blur, plate sizes and occlusion. The 6.8 s two-line bus crop and 21.6 s nearby crop contain visible characters; some other crops are difficult. | The whole dataset is not uniformly unreadable. Readability totals are unknown; do not infer them from OCR scores or rejection counts. |
| Frame selection | Only up to three samples retained, ranked by plate area × detector score. OCR attempted selectively when vehicle is near/large. No sharpness/perspective ranking. | Larger is not necessarily clearer. Need human-readable/correctness ranking of same-passage crops before changing selection. Source timeline exposes frames not retained. |
| OCR cadence | `2.4 - 1.8 < 0.6` in floating point; original rule skips the exact intended boundary. | Independently reproduced defect. New `recorded-onnx-v2` uses a 1 ns comparison tolerance; old v1 replay unchanged. No inference or decision threshold tuning. |
| Crop mapping/resizing | Re-decoded all original 39 crops from their PTS and original-coordinate boxes; PNG pixels exactly match. ROI top offset applied to vehicle and plate crops. Detector letterbox scale/padding are undone before slicing. | No observed crop-coordinate corruption. Equality establishes implementation consistency, not that the detector chose the physical plate correctly. |
| Color order / tensor format | Crop arrays are BGR; OCR converts to RGB uint8, bilinear 128×64. Unit probe checks channel values, dtype and shape; actual OCR on every crop reproduced raw slots/text/scores. | No demonstrated channel swap defect. Recognition resize intentionally distorts aspect ratio to the model's trained input shape; do not “fix” it without an evaluated alternative. |
| OCR model limitations | Small fixed ten-slot CCT global model; no India-specific validated performance. Visual first-passage crop has characters that do not correspond fully to its raw result. High score can coexist with unsupported output. | At least qualitative model-reading problems are visible. Exact error rate and condition dependence need independent transcriptions. No switch of model justified solely by rejection totals. |
| Supported plate formats | `plates.py` accepts only illustrative `AA00AA0000`; no general Indian grammar/registration validation. Position-specific O/I substitutions only, no missing-character generation. Some visible source plates have longer series shapes. | A genuine scope limitation contributing to unsupported results, not proof every unsupported OCR string is correct. Audit against official registration formats and human labels before broadening. No grammar or thresholds changed here. |
| Consensus behavior | Every original machine result reproduced exactly from raw retained inputs; duplicates use per-frame maximum, unsupported frames count in denominator. | Six review outcomes are expected under the existing policy. Whether that policy is useful requires false-accept and readable-rejection evaluation. Do not drop difficult frames solely to inflate scores. |

Inspected original/crop examples include crossing times 1.0, 6.8, 21.6 and approximately 34 s; multiple other retained examples are available through the review console. These qualitative observations are **not** user ground-truth labels. Real strings remain confined to authorized local evidence/UI.

Model source/configuration: [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr) expects plate crops; [release plate configuration](https://github.com/ankandrew/fast-plate-ocr/releases/download/arg-plates/cct_xs_v2_global_plate_config.yaml) describes the selected ten-slot RGB model. The [MorseTech plate detector](https://huggingface.co/morsetechlab/yolov11-license-plate-detection) is plate-specific; its reported benchmarks are not adopted as RoadEye results. Immutable weight URLs/digests, exports and license notes remain in `recorded/models.json`. No weights were changed or downloaded during this audit.

## Small verified change and before/after

| Measurement, same [0,60) development interval | Original v1 | Separate v2 |
|---|---:|---:|
| Decoded / sampled frames | 1500 / 300 | 1500 / 300 |
| Predicted crossings / retained plate-proposal passages | 25 / 22 | 25 / 22 |
| Accepted / review / rejected / pending | 2 / 6 / 17 / 0 | 2 / 8 / 15 / 0 |
| Retained lossless crops | 39 | 42 |
| Verified evidence objects / missing | 99 / 0 | 102 / 0 |
| Acceptance coverage of predicted passages | 8% | 8% |
| Full-plate accuracy | Not yet measured | Not yet measured |

Crossings at 11.2 and 54.6 s changed from rejection to review; no additional automatic acceptance was obtained. New runs snapshot processing/inference source-file hashes and retain the same-frame vehicle box with every plate crop. Original runs retain their crossing vehicle box but did not store a vehicle box at each crop PTS; the UI states this absence rather than drawing the crossing box on a different-time frame. The unchanged MP4 permits independent source review.

New acceptance executed a SIGKILL after three durable publications at 6.0 s, recovered on attempt two, then replayed. Passage/observation IDs, outcomes and 51 done jobs were unchanged after replay. CPU inference took 25.758 s recovered and 25.272 s replay; full acceptance 88.986 s. A read-only audit independently reproduced all 42 OCR records and 25 decisions and verified the source pixels. These timings measure one clip, not multi-feed capacity.

## Metrics available after human review

Current review coverage: **0/25 original predictions and 0/25 v2 predictions**; source-timeline completeness has not been declared. Ground-truth vehicle count, detector precision/recall, duplicates, misses, readable-only recognition, incorrect automatic readings and readable rejection rate are **not yet measured**. Zero existing labels does not mean zero errors.

The new evaluation endpoint calculates the following from the latest independent label revisions and immutable original machine decisions:

- **Predicted passages P:** all stored line-crossing predictions. **Acceptance coverage:** automatically accepted original machine observations / P, even before duplicate correction.
- **Ground-truth count G:** predictions labelled valid unique vehicles + separately marked valid missed vehicles. Available only after every prediction is resolved, every missed marker resolved, and a reviewer confirms the complete run timeline. Duplicate/incorrect predictions do not enter G.
- **Readable denominator R:** all fully readable unique vehicles in G, including readable missed vehicles. Partial/unreadable vehicles remain in G but not R.
- **Correct full readings C:** exact match of the machine-selected plate against independently transcribed fully readable valid predictions; missed vehicles contribute zero. Whitespace/hyphen/case cleanup is allowed for comparison; no character substitution in labels. **Readable-only recognition = C/R** and **overall correct-reading coverage = C/G**, emitted only after complete passage/readability/timeline review.
- **Incorrect automatic readings:** accepted valid readable predictions whose original machine text differs from the human transcription. The response reports the number of comparable accepted transcriptions; unreadable/unassessed accepted records remain unknown, not presumed correct. Accepted duplicate/incorrect passage predictions are reported separately.
- **Correct/incorrect/missing plate detections:** human passage-level assessment counts, not per-box detector AP. **Readable rejected/reviewed:** fully readable valid predicted vehicles without automatic acceptance, reported alongside readable missed vehicles. Partial/unreadable counts include marked misses.

Review labels cannot alter processing or correct the machine result. Operational investigator corrections remain a different API/table; metrics deliberately ignore those corrections (tested). Revisions retain actor, self-reported reviewer identity, notes and timestamp. Private CSV/labels/evidence are never committed. See [numbered review instructions](recorded_video_demo.md#independent-human-review-after-this-audit).

## Development and evaluation boundary

The first 60 seconds are **development data**: they have been inspected and used to diagnose/change cadence. Reserve a proposed [120,180) interval for evaluation, with the intervening minute excluded as a guard; verify vehicle passage boundaries before fixing the split. No inference or visual tuning on that interval was performed in this audit. This does not certify that nobody has previously viewed it.

The current processor accepts a zero-based duration only; it has **no start-window control yet**. Before a holdout evaluation, implement explicit interval/warm-up/finalization semantics, exclude overlapping passages, freeze model/code/policy, label independently, then run once. Do not call a full [0,180) rerun a held-out evaluation unless results are correctly separated and passage overlap audited. A later segment of the same fixed camera still does not establish generalization to new cameras, weather, Indian plate types or cities.
