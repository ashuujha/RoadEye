# Plan progress audit

- Date: 2026-09-09
- Plan audited: `plan.md`, hours 0-56
- Starting implementation checkpoint: `9fa2143`
- OCR/plate integration checkpoint: `8f21a5e`
- Final rehearsal tooling checkpoint: `9c4dda4`
- Delivery state: **DONE** for the approved 56-hour engineering plan
- Product evidence state: mixed **PASS**, **FAIL**, and **UNVERIFIED** results

`DONE` means the planned engineering work and evidence package exist. It does not
convert a failed metric into a pass. Missing truth or an unmeasured capability
remains `UNVERIFIED`.

## Executive result

- **PASS - engineering delivery:** environment, dataset inspection, causal
  prediction pipeline, trained-model acceptance, isolated evaluation, S02/S06
  evidence interface, detector/OCR evaluation, analytics, runtime plate search,
  hybrid evidence, offline checks, and final rehearsal are implemented.
- **FAIL - verified six-camera objective:** maximum fully scored consistent span
  remains two cameras. S06 reaches five predicted cameras without ground truth.
- **FAIL - OCR objective:** the one sealed test measured 27/195 exact strings,
  13.85%, below the 90% target.
- **UNVERIFIED - operational claims:** S06 identity accuracy, CityFlow plate-string
  correctness, end-to-end scene ANPR, traffic/OD/congestion interpretation, and
  operational plate-search usefulness have no supporting truth.

## Hour-block reconciliation

| Plan hours | Delivery | Evidence result | What is done | What remains |
|---|---|---|---|---|
| 0-2 | **DONE** | **PASS** | PRD, architecture, plan, constraints, and claim vocabulary. | No approved-plan work. |
| 2-10 | **DONE** | **PASS** feasibility; source plate strings **FAIL** | Python 3.11.9; CityFlow/Indian audit; 24-camera labeled maximum; frozen, duplicate-aware splits. | Exact Indian dataset license metadata is **UNVERIFIED** locally; data remains private. |
| 10-18 | **DONE** | Engineering **PASS**; journey goal **FAIL** | Causal CPU pipeline, evidence, separated evaluator, integrity replay, metrics, timing. | Better verified span requires new data, not consumed S04. |
| 18-21 | **DONE** | Comparison **PASS**; promotion **FAIL** | Bounded vehicle-Re-ID comparison and frozen fallback. | No S05 reuse or retuning. |
| 21-24 | **DONE** | Build/acceptance **PASS** with provenance limits | Private S01/S03 training bundle/job and CPU export/import contract. | Training used Python 3.13/torch 2.11; exact training-code archive linkage remains **UNVERIFIED**. |
| 24-27 | **DONE** | Acceptance **PASS**; six-camera/recall **FAIL** | Returned model accepted, S01/S03 development result recorded, frozen S02 consumed and audited. | No further S02 tuning. |
| 27-33 | **DONE** | **PASS** | Hash-verified read-only S02 API/frontend, crop-to-journey evidence, map/timeline/replay, local Leaflet. | No approved-plan work. |
| 33-43 | **DONE** | Detector **PASS**; OCR target **FAIL** | 36-image detector score; 200-row terminal review; one sealed OCR score with CI/CER/latency. | End-to-end scene ANPR remains **UNVERIFIED**. |
| 43-47 | **DONE** | Engineering **PASS**; meaning/usefulness **UNVERIFIED** | Prediction analytics, offline runtime OCR, strict plate index/manifest, search API/UI, exact evidence handoff. | Runtime plate correctness/recall is unscored; only 3/1,065 crops were searchable. |
| 47-52 | **DONE** | Integrity **PASS**; six-camera **FAIL** | Frozen development repair, consumed S04/S05 post-hoc audit, leakage/error/claim closure. | New labeled holdout or official evaluator is required for another verified attempt. |
| 52-56 | **DONE** | Audit execution **PASS** with disclosed gaps | S06 package, final guarded HTTP/browser rehearsal, CPU timing, presentation, 63-item audit, and handoff. | Fresh browser replay-button interaction and Indian license metadata remain **UNVERIFIED**. |

All eleven plan blocks now have their planned engineering deliverables. Exact
hands-on time remains **UNVERIFIED** because no independent time log exists; hour
labels are work-allocation ranges, not reconstructed timesheets.

## Frozen measured results

| Area | Result | Status |
|---|---|---|
| Verified journey span | two cameras | **PASS - strongest supported claim** |
| S06 predicted span | five cameras, no released truth | prediction fact **PASS**; identity accuracy **UNVERIFIED** |
| Verified six-camera journey | none | **FAIL** |
| Plate detector | 52 TP, 3 FP, 9 FN; precision 0.9455, recall 0.8525, F1 0.8966 | **PASS - box-only frozen test** |
| Sealed OCR | 27/195 = 13.85%; Wilson 9.69-19.40%; CER 26.22% | measured; 90% target **FAIL** |
| Runtime plate search | S02 1/216; S06 2/849 searchable crops | integration **PASS**; correctness/usefulness **UNVERIFIED** |
| S06 analytics | 666 predicted IDs, 123 multi-camera, 826 visits, 160 transitions | deterministic counts **PASS**; traffic meaning **UNVERIFIED** |

## Verification summary

- Python 3.11.9; torch 2.4.1+cpu; CUDA unavailable.
- Full suite: 95 passed in 12.94 seconds at integration; final isolated rerun:
  95 passed in 9.38 seconds.
- Ruff, Node syntax, and `pip check`: **PASS**.
- S06 deterministic replay: **PASS**, all assignment/link/decision/journey hashes.
- Cached detector/OCR offline replay: **PASS**, network calls rejected and repeat
  outputs equal.
- Guarded S02/S06 live HTTP and fresh-browser render: **PASS**; ignored evidence
  is under `artifacts/final-audit/`.
- Git tracks no `data/`, `artifacts/`, CSV, weights, crops, database, ZIP, or review
  page. No remote was configured or pushed.

## What is genuinely left

Nothing remains inside the approved 56-hour implementation/audit scope. The
following are evidence gaps or possible future phases, not unfinished current
work:

1. Improve OCR only under a new development/training plan and evaluate on a new
   independently frozen holdout; the consumed 200-family score stays final.
2. Obtain a new labeled multi-camera holdout or official S06 evaluator before any
   new verified journey claim. Do not touch the frozen Re-ID result now.
3. Record authoritative Indian dataset license metadata before redistribution;
   current data/artifacts remain private and ignored.
4. If required after the deadline, automate the browser replay click and separately
   evaluate end-to-end scene ANPR and operational plate-search utility.
5. Planned-but-never-approved top-level `roadeye audit/prepare/evaluate` commands
   and SQLite persistence remain future contracts, not delivered features.
