# Plan progress audit

- Date: 2026-09-08
- Plan audited: `plan.md`
- Implementation head audited: `ef1d9a2`
- Overall delivery state: **PARTIAL**
- Overall closure finding: **UNVERIFIED**

## Scope and method

This audit maps the current repository, commits, reports, ignored runtime
artifacts, and fresh verification results to each hour block in `plan.md`.
`DONE` means that the planned engineering activity was implemented and audited;
it does not mean that its product target passed. `PARTIAL` means that one or more
explicit deliverables in that block remain unfinished. Findings use `PASS`,
`FAIL`, and `UNVERIFIED` independently of delivery state.

Evidence inspected includes all 18 local commits through `ef1d9a2`, the tracked
phase reports under `reports/`, current configurations and source/tests, and the
available ignored artifacts under `data/` and `artifacts/`. A scoped Graphify
query was used for navigation; conclusions below were checked against the source
reports and current commands. No Claude context file was present.

## Executive result

- **PASS - core delivery foundation:** Python 3.11, frozen data protocols,
  causal CPU association, isolated evaluation, trained Re-ID loading, the local
  evidence interface, Indian detector evaluation, OCR review tooling, S06
  prediction, and prediction-only analytics are implemented.
- **FAIL - verified six-camera journey:** the best fully scored,
  identity-consistent result remains two cameras. S06 predicts at most five of
  six cameras and has no released ground truth.
- **FAIL - sealed OCR readiness:** all 200 test families still have a missing
  review status; zero are currently eligible for the required minimum of 150
  readable strings.
- **UNVERIFIED - sealed OCR and end-to-end ANPR quality:** no test full-string
  accuracy exists, and detector output has not been evaluated end to end through
  OCR.
- **PARTIAL - product completion:** plate search, plate/vehicle hybrid evidence,
  and final whole-project closure remain incomplete. Aggregate prediction
  analytics are implemented but intentionally remain `UNVERIFIED` as traffic
  measurements.

## Hour-block reconciliation

| Plan hours | Delivery | Finding | Evidence completed | Work left |
|---|---|---|---|---|
| 0-2 | **DONE** | **PASS** | PRD, architecture, plan, feasibility protocol, claim boundaries, and repository instructions were created in `988b544`. | Synchronize stale status wording in planning documents during final closure. |
| 2-10 | **DONE** | **PASS** for environment, CityFlow coverage, and benchmark capacity; **FAIL** for supplied plate strings | Python 3.11.9 environment, CityFlow archive audit, 24-camera labeled maximum, Indian archive audit, duplicate grouping, and frozen splits are recorded in `reports/feasibility-gate.md` and `configs/anpr-split.json`. The approved manual-transcription pivot provides an honest 200-family test benchmark. | Supplementary Roboflow/IEEE sources remain **UNVERIFIED** but were explicitly time-capped and are not needed for the current reduced benchmark. |
| 10-18 | **DONE** | **PASS** engineering; **FAIL** journey target | Full frozen S04 import, causal CPU embeddings, association, evidence, separated evaluator, integrity replay, timing, and metrics are in `reports/phase2-audit.md`. | No legitimate retuning remains on S04. A better verified journey requires new development/evaluation evidence, not more use of this consumed diagnostic. |
| 18-21 | **DONE** | **PASS** bounded comparison; **FAIL** model-promotion and six-camera gates | VeRi adapter parity, causal quality prefixes, S01-only selection, frozen S05 evaluation, error analysis, CPU/offline checks, and fallback selection are in `reports/reid-audit.md`. | No further S05 selection is allowed. The failed replacement and low recall remain historical results. |
| 21-24 | **DONE** | **PASS** | Private S01/S03 identity-disjoint bundle, Colab job, training/evaluation contract, provenance, and CPU export/load checks were built in `4a75456`; the later returned result was accepted. | No build work remains. The recorded Python/torch training-version deviation and missing cryptographic job-code link remain provenance limitations. |
| 24-27 | **DONE** | **PASS** acceptance/isolation; **FAIL** six-camera and recall outcomes | Returned epoch-7 model acceptance, S01/S03 development improvement, exact CPU loading, frozen S02 run, deterministic replay, evaluation, error analysis, and timing are in `reports/reid-trained-s02-audit.md`. | S02 is consumed and cannot be retuned or reused as fresh evidence. |
| 27-33 | **DONE** | **PASS** | Frozen S02 read-only API, crop selection, source frames, map, timeline, replay, local Leaflet assets, browser smoke, and GT-free runtime allowlist are in `reports/frontend-audit.md`. | Plate search was deferred. Analytics listed as deferred in this historical report were implemented later. |
| 33-43 | **PARTIAL** | **PASS** detector/development workflow; **FAIL** test readiness; **UNVERIFIED** sealed OCR | Indian inventory/splits, 30-epoch CPU detector, one sealed detector test, EasyOCR preparation, 50-family development review, `color_upscale` freeze, 200 test predictions, sealed review page, strict status gate, and ground-truth-blind triage are complete. | A human must review all 200 test families, assign only `reviewed`, `corrected`, or `unreadable`, retain at least 150 readable rows, and then run the one sealed test evaluation. End-to-end scene ANPR remains unmeasured. |
| 43-47 | **PARTIAL** | **PASS** prediction analytics; **UNVERIFIED** operational meaning and plate integration | `/api/analytics`, camera visit intensity, predicted OD endpoints, transition-support proxies, scaled camera markers, S06 aggregate audit, tests, live HTTP, and browser smoke are complete in `ef1d9a2`. | Plate search and plate/vehicle hybrid evidence are not implemented. They remain blocked on sealed OCR evidence and an approved integration boundary that does not copy Indian benchmark truth into CityFlow journeys. |
| 47-52 | **PARTIAL** | **PASS** frozen repair/integrity work; **FAIL** six-camera outcome | S01/S03-only calibration, frozen S04/S05 post-hoc runs, leakage boundaries, deterministic replay, error analysis, and claim corrections are in `reports/reid-six-camera-repair-audit.md`. | Do not tune consumed S02/S04/S05. Final cross-component leakage, timing, and claims closure must be repeated after the OCR/plate decision. A fresh verified six-camera result needs a new approved labeled holdout or official evaluator. |
| 52-56 | **PARTIAL** | **PASS** S06 integration/rehearsal; **FAIL** six-camera prediction; **UNVERIFIED** S06 accuracy | Complete six-camera S06 input, frozen-policy CPU prediction, evidence export, deterministic replay, explicit demo config/disclosure, live API smoke, and tracked evidence package are in `reports/s06-demo-audit.md`. | The whole-product final package cannot close while sealed OCR, plate search/hybrid scope, and final integrated audit remain open. S06 itself has no local scoring path. |

Seven of the eleven plan blocks have all stated engineering activities delivered.
Four blocks remain partial: 33-43, 43-47, 47-52, and 52-56. This is a block
count, not a claim about hands-on hours consumed.

## Current measured evidence

### Environment and repository integrity

- **PASS:** `.venv\Scripts\python.exe` is Python 3.11.9.
- **PASS:** fresh full suite: **80 passed in 6.51 seconds**.
- **PASS:** `python -m ruff check .` reports all checks passed.
- **PASS:** `python -m pip check` reports no broken requirements.
- **PASS:** Git tracks no files beneath `data/` or `artifacts/`, and no tracked
  `.pt`, `.pth`, ZIP, database, or CSV artifact was found.
- **UNVERIFIED:** the host does not expose model/reasoning configuration, so
  Astra 6/xhigh cannot be confirmed. The host is in Default mode, not Plan Mode.

### CityFlow and journey evidence

- **PASS:** the inspected archive has released identities spanning at least 24
  S04 cameras, so source-data camera coverage exceeds six.
- **PASS:** frozen S06 replay reproduced 1,674 baseline tracklets, 826 embedded
  tracklets, 160 links, 666 predicted IDs, and all prediction hashes without GT
  or scoring access.
- **FAIL:** S06 maximum predicted coverage is five cameras, not six.
- **FAIL:** across scored evidence the maximum fully consistent journey remains
  two cameras. No unused locally labeled CityFlow scenario remains for a fresh
  held-out six-camera claim.

### Indian ANPR evidence

- **PASS:** the sealed detector test measured 52 TP, 3 FP, and 9 FN over 61
  boxes: precision 0.9455, recall 0.8525, and F1 0.8966 at confidence/IoU 0.50.
- **PASS:** development review produced 48 readable and two unreadable plates.
  Frozen `color_upscale` development performance is 10/48 exact strings
  (0.2083) with CER 0.2309.
- **PASS:** the current triage revalidated exactly 200 frozen test predictions
  and produced 50 `manual_attention`, 100 `standard`, and 50 `quick_check` rows
  without using ground truth.
- **FAIL:** current readiness is reviewed 0, corrected 0, unreadable 0, missing
  200, readable 0/150. The scoring command aborts before loading truth.
- **UNVERIFIED:** sealed test accuracy, the 90% target, and end-to-end scene ANPR.

### Demo and analytics evidence

- **PASS:** the default `configs/demo.json` remains the frozen S02 evidence
  interface; `configs/demo-s06.json` is an explicit unverified S06 alternative.
- **PASS:** crop-to-journey selection, boxed source frames, chronological replay,
  approximate-position labels, interpolation labels, and uncalibrated-score
  labels are implemented locally.
- **PASS:** S06 prediction aggregates contain 666 predicted IDs, 123
  multi-camera predicted IDs, 826 observed runtime visits, and 160 predicted
  transitions across six cameras.
- **UNVERIFIED:** those aggregates inherit association errors and are not traffic
  volume, verified OD flow, congestion, or route travel-time measurements.

## Remaining work in dependency order

1. **Human sealed-test review - BLOCKED on user action.** Review all 200 test
   plate families in `artifacts/anpr/transcription-review.html`, export to the
   ignored `data/anpr/transcriptions.csv`, and preserve exact terminal statuses.
2. **One-time sealed OCR evaluation - NOT STARTED.** After readiness passes,
   execute `scripts/run_anpr.py evaluate-ocr-test` once. Record full-string
   accuracy, Wilson interval, CER, readable/unreadable denominators, and CPU
   latency exactly, even if the result is below 90%.
3. **Plate search and hybrid evidence - NOT STARTED.** Define and approve a
   ground-truth-safe runtime boundary based on the sealed result. Never attach
   Indian benchmark labels to CityFlow identities or treat OCR suggestions as
   reviewed truth.
4. **Final integrated audit - NOT STARTED.** Re-run offline/network/GT isolation,
   CPU timing, frontend/API smoke, claim review, artifact allowlist checks, and
   the full test suite after the plate decision. Package one final status report.
5. **Verified six-camera repair - BLOCKED on new evidence.** Existing labeled
   scenarios are consumed. Further progress needs new approved camera-diverse
   development data followed by a new labeled holdout, or access to an official
   S06 evaluator. More tuning on S02/S04/S05 is prohibited.

The planned top-level `roadeye audit`, `roadeye prepare`, and `roadeye evaluate`
commands remain future contracts; only `roadeye serve` exists. SQLite is named in
`architecture.md`, but the implemented prediction runtime uses hash-verified JSON
artifacts and no SQLite persistence layer exists. Neither item should be called
complete without a separately approved scope change.

## Plan and document drift

- **FAIL:** the `plan.md` summary table still labels 33-43 as generally in
  progress and does not show the partial completion of 43-47 analytics, although
  later sections do. It should be normalized during final claims cleanup.
- **FAIL:** `agents.md` and `reports/anpr-audit.md` contain historical statements
  that analytics are not implemented. The current source, PRD, architecture,
  later plan section, and analytics audit show that prediction-only analytics
  are implemented; plate search remains absent.
- **UNVERIFIED:** commit labels allocate work to the 56-hour plan but no
  independent hands-on time log exists. Exact budget consumption cannot be
  reconstructed from commit timestamps, so budget adherence is not asserted.
- **PASS with deviation:** phases were executed out of numerical order to address
  blockers; the S06 52-56 checkpoint preceded the 43-47 analytics checkpoint.
  The work remained scoped, but exact hour accounting is unverified.

## Checkpoint decision

The repository is not ready for a final `PASS` against `plan.md`. The next valid
checkpoint is the human sealed-test review, followed by exactly one frozen OCR
test evaluation. Until that evidence exists, plate search/hybrid integration and
the final whole-project audit remain blocked. No further CityFlow tuning should
occur on consumed scenarios, and the honest demo framing remains a two-camera
verified maximum with larger predictions explicitly unverified.
