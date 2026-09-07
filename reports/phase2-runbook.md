# Phase 2 CPU baseline and evidence

Run commands from `C:\RoadEye`. Python 3.11 and the existing editable installation are used. This phase has no API or frontend.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts/run_phase2.py scripts/verify_phase2.py

# Explicit first-time checkpoint download; never done implicitly by inference.
.\.venv\Scripts\python.exe -m roadeye.phase2 fetch-weights

# First run extracts real crops and computes CPU features. Later runs validate/reuse cache.
.\.venv\Scripts\python.exe -u -m roadeye.phase2 run

# Repeat inference with GT-file and network access forbidden; check real-data prefixes.
.\.venv\Scripts\python.exe -u scripts/verify_phase2.py

# Separate offline evaluator is the only application module allowed to open identity labels.
.\.venv\Scripts\python.exe -u -m roadeye.evaluation
```

`scripts/run_phase2.py` remains a compatible command entry point. The default configuration is `configs/phase2.json`; it references the existing frozen `configs/feasibility-window.json`. Changed inputs fail cache validation; use a new `--output` directory for a deliberately different experiment. Do not tune configurations using this S04 diagnostic's results and continue calling it held-out evaluation.

## Artifact contract

All run artifacts are under ignored `artifacts/phase2-repaired/`. The old `artifacts/phase2/` results are preserved but superseded: their zero-GT-coverage precision value is invalid.

| Artifact | Meaning |
|---|---|
| `prepared.json` | Input and artifact checksums, model/preprocessing provenance, actual preparation timing and counts |
| `observations.jsonl` | Every predicted MTSC observation in the frozen interval; no GT fields |
| `tracklets.json` | Eligible tracklet keys, first-three crop/frame/box evidence, appearance-ready timestamp |
| `embeddings.npz` | Aligned keys and normalized 2048-dimensional CPU appearance features |
| `excluded_tracklets.json` | Explicit reasons a baseline tracklet has no complete appearance prefix |
| `topology.json` | Calibration-derived reference positions and a conservative proximity graph |
| `assignments.json` | Predicted local tracklet key to independent RoadEye global ID |
| `links.json` | Accepted links, raw cosine scores, margins, temporal/distance evidence, and source observations |
| `decisions.json` | Every new-ID/link decision, top candidates and rejection counts |
| `journeys.json` | Ordered observed visits with identification timestamps and evidence; no road route claim |
| `run.json` | Prediction checksums, counts, and measured association duration |
| `integrity.json` | Reproducibility, offline/GT isolation, and real-data causal-prefix audit |
| `evaluation/metrics.json` | Measured metrics, denominators, mapping coverage and limitations |
| `evaluation/tracklet_gt_mapping.json` | Evaluator-only identity mapping, coverage and purity; never an inference input |

The canonical tracklet key includes partition, scenario, camera and baseline local ID. Global IDs derive from the founding predicted tracklet key and are stable within this dataset/run configuration. Model/baseline versions remain part of run provenance; do not treat IDs as a cross-model registry.

## Metric interpretation

The evaluator matches boxes at each camera/frame using one-to-one IoU >= 0.5. A tracklet identity is usable only with at least three matched observations, at least 50% observation coverage, and at least 80% identity purity. Unmatched and ambiguous tracklets are counted explicitly.

Direct-link precision uses links whose two endpoints have usable identity mappings. Other links are unscored, not false. Their count, evaluation coverage, and possible full-link precision bounds accompany the metric. Global-ID pairwise precision/recall uses all scored cross-camera pairs, including fragmented groups and missed same-identity joins. GT camera-visit coverage exposes baseline misses separately. Appearance Rank-1/mAP uses a prior-observation gallery restricted to scored tracklets, so it is a diagnostic and is not directly comparable with full-system link precision or the official benchmark.

Scores are uncalibrated cosine similarities. The MTSC input confidence column is a baseline tracking score, often constant one; it is not a measured detector confidence or probability.

RoadEye decisions use only observations and appearance prefixes available at their recorded decision time. The provided baseline local tracking algorithm's own upstream causality and training provenance have not been independently verified. Exact camera GPS and a verified road graph are absent; inverse-calibrated ROI reference points are explicitly approximate.

S04 was chosen during feasibility using released identity coverage. Preserve the distinction between this fixed diagnostic and a fresh unbiased holdout. Future tuning belongs on S01/S03 or a newly approved development split, followed by a separately frozen evaluation slice. Indian OCR is independent of this phase.
