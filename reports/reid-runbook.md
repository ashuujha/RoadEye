# Bounded Phase 2 Re-ID comparison

This checkpoint extends the repaired Phase 2 implementation. It adds no service,
database, frontend, GPU requirement or CityFlow training. Use Python 3.11 from the
existing `.venv`. Weights, source crops and generated runs remain ignored.

## Development and selection

The experiment is declared in `configs/reid-experiment.json`. Windows use all
scenario cameras in the first 180 seconds, independent of identity annotations.
S01 is development; S05 is evaluation. The earlier S04 diagnostic stays intact.

```powershell
.venv/Scripts/python.exe scripts/freeze_reid_windows.py
.venv/Scripts/python.exe scripts/compare_reid.py initialize
.venv/Scripts/python.exe -m roadeye.phase2 fetch-weights --config configs/reid-dev-veri_prefix.json
.venv/Scripts/python.exe scripts/verify_vehicle_encoder.py --fetch-reference
.venv/Scripts/python.exe scripts/compare_reid.py develop --variant imagenet_prefix
.venv/Scripts/python.exe scripts/compare_reid.py develop --variant veri_prefix
.venv/Scripts/python.exe scripts/compare_reid.py develop --variant veri_quality
.venv/Scripts/python.exe scripts/compare_reid.py select
```

Downloads occur only in the explicitly named fetching commands. The parity
script compares raw descriptors with pinned upstream operations on synthetic
inputs; it is not an accuracy benchmark. `develop` runs inference, then invokes
the offline evaluator on S01 and scores the predeclared grid. Per-candidate
assignments, links, metrics and hashes are retained under
`artifacts/reid-development/<variant>/development-grid/`.

`select` writes `configs/reid-evaluation.json`, `reports/reid-development.json`
and `reports/reid-selection.json`. It refuses to overwrite an existing selection.
Do not regenerate or replace a historical selection to improve an evaluation
result. For a repeat of the already frozen evaluation, use its committed config,
source revision and development report; start a new output directory if cache
inputs differ. A later experiment requires a new approved protocol and artifacts.

## Frozen evaluation and integrity

After development selection has been committed locally:

```powershell
.venv/Scripts/python.exe -m roadeye.phase2 run --config configs/reid-evaluation.json --output artifacts/reid-evaluation-s05
.venv/Scripts/python.exe scripts/verify_phase2.py --config configs/reid-evaluation.json --output artifacts/reid-evaluation-s05 --check-encoder
.venv/Scripts/python.exe -m roadeye.evaluation --output artifacts/reid-evaluation-s05
.venv/Scripts/python.exe scripts/analyze_reid_errors.py --output artifacts/reid-evaluation-s05
```

The runtime verifies frozen text fingerprints (normalizing CRLF/LF for checkout
portability), model hashes, data metadata and artifact hashes. Dataset/weight
hashes remain byte-exact. The integrity check reruns inference without rewriting
the original run metadata, blocks GT/network access, verifies every evidence crop,
checks decisions at 50/100/150 seconds, and optionally recomputes three cached
tracklet descriptors on CPU. No S05 labels are used before these predictions.

Artifacts include `prepared.json`, `tracklets.json`, `embeddings.npz`,
`excluded_tracklets.json`, `observations.jsonl`, `topology.json`, `assignments.json`,
`links.json`, `decisions.json`, `journeys.json`, `run.json`, `integrity.json`,
and separate `evaluation/metrics.json` / `evaluation/tracklet_gt_mapping.json`.
The prepared source manifest records explicitly excluded invalid baseline rows.

Report raw counts, unknown links, crop exclusions, mapping coverage, link precision,
pairwise precision/recall (both assigned-only and all-mappable denominators),
causal retrieval, maximum fully scored consistent camera coverage, and CPU wall
times. Concurrent development-run timings are not isolated latency benchmarks.
`analyze_reid_errors.py` reads the finished evaluator mappings and measures
optimistic pair-level candidate opportunities before group constraints; its
labelled-gallery diagnostic is not end-to-end accuracy and cannot change settings.
S01 scores are development results; S05 is a fixed local evaluation with partial
labels and shared geography with S04. A long predicted group alone is not a
verified long journey.

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check src tests scripts/run_phase2.py scripts/verify_phase2.py scripts/compare_reid.py scripts/freeze_reid_windows.py scripts/verify_vehicle_encoder.py
.venv/Scripts/python.exe -m pip check
git diff --check
```

Stop at the audit/local-commit checkpoint. Do not start frontend, OCR, fine-tuning
or a further evaluation/tuning cycle without the user's next direction.
