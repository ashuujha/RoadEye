# Hours 52-56 final integrated audit checklist

- Prepared: 2026-09-09
- Execution state: **UNVERIFIED** until every applicable item is rerun after OCR
  scoring and runtime plate-index wiring
- Scope rule: verify frozen Re-ID outputs; do not retrain, recalibrate, retune, or
  rescore S02/S04/S05 as fresh evidence
- Result vocabulary: every audit finding is `PASS`, `FAIL`, or `UNVERIFIED`

The final integrated audit will verify exactly the following 63 items. A missing
artifact, skipped command, absent denominator, or unavailable evidence is
`UNVERIFIED`, never `PASS`.

## A. Repository and environment

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| A01 | Local commit boundary | Record starting and ending commit IDs; final scoped changes are locally committed; no push or remote configuration occurs. |
| A02 | Python runtime | `.venv\Scripts\python.exe --version` reports Python 3.11.x and that interpreter runs every Python check. |
| A03 | Dependency integrity | `.venv\Scripts\python.exe -m pip check` exits 0; pinned `requirements-cpu.txt` and editable package metadata remain compatible. |
| A04 | Python tests | `.venv\Scripts\python.exe -m pytest -q` exits 0; record exact passed/failed/skipped counts and elapsed time. |
| A05 | Static checks | `.venv\Scripts\python.exe -m ruff check .` and `node --check test_frontend\app.js` both exit 0. |
| A06 | Tracked-file hygiene | `git ls-files` contains no file under `data/` or `artifacts/` and no raw datasets, transcription CSVs, weights, crops, databases, credentials, or generated review pages. |
| A07 | Working tree attribution | List pre-existing/user-owned changes separately from final checkpoint files; no unrelated file is staged or committed. |

## B. Frozen inputs, provenance, and licenses

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| B01 | CityFlow input provenance | Dataset path, scenario/window, archive/source record, license constraints, and all configured input hashes resolve exactly. |
| B02 | Indian benchmark provenance | Frozen split, duplicate-family grouping, source hashes, review CSV hash, and dataset/license/redaction rules are recorded and internally consistent. |
| B03 | Model provenance | Vehicle Re-ID, detector, and OCR model manifests resolve to the exact local weight hashes and versions; startup performs no download. |
| B04 | Prediction artifacts | Prepared/run/journey/link/tracklet/topology hashes validate before API repository construction for default S02 and optional S06. |
| B05 | Runtime allowlist | Only explicitly required prediction artifacts plus the explicitly configured, SHA-256-pinned optional plate index can be opened by the demo adapter. |
| B06 | Final evidence package | Every numeric slide claim names a tracked report/artifact, exact denominator, scope, and relevant limitation. |

## C. Ground-truth and data-boundary isolation

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| C01 | CityFlow identity isolation | Demo startup and all HTTP routes succeed with access to `gt.txt` and `evaluation/` blocked; no response contains released identity mappings. |
| C02 | Prediction-before-evaluation boundary | Existing frozen run timestamps/hashes show prediction artifacts were written before their evaluator output; no final task rewrites those predictions. |
| C03 | Indian truth isolation | Test transcriptions are read only by readiness/scoring commands, never by `roadeye.demo`, the browser, analytics, or plate-index generation. |
| C04 | Prohibited plate data | Plate index/API/frontend contain no owner, person, address, evaluator identity, benchmark transcription, or inferred ownership field. |
| C05 | Network isolation | Offline verification and a monitored server rehearsal show no hidden model, tile, font, analytics, or other network request. |
| C06 | Path containment | Configured runtime, dataset, frontend, crop, frame, and optional plate-index paths reject traversal outside their allowed roots. |

## D. Frozen vehicle journey evidence

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| D01 | No Re-ID modification | Diff from the pre-phase checkpoint shows no Re-ID weights, training data, thresholds, association policy, S02/S04/S05 prediction, or evaluation mapping changed. |
| D02 | Default demo | `configs/demo.json` still targets frozen S02 and is the documented default. |
| D03 | Verified claim | Final copy states the maximum fully scored identity-consistent journey is two cameras and does not promote 3/3 evaluable links to broad accuracy. |
| D04 | S06 determinism | `.venv\Scripts\python.exe scripts\run_s06_demo.py verify` reproduces assignment, link, decision, and journey hashes. |
| D05 | S06 claim | Final copy states maximum predicted span five cameras, no released GT, accuracy/identity consistency `UNVERIFIED`, and verified six-camera criterion `FAIL`. |
| D06 | Evidence semantics | Every journey visit remains observed; every map segment remains interpolated; approximate positions and uncalibrated scores retain their labels. |

## E. Detector and sealed OCR evaluation

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| E01 | Review readiness | `scripts\run_anpr.py validate-ocr-test` reports exactly 200 terminal rows, zero missing/unrecognized, and at least 150 `reviewed` or `corrected`. |
| E02 | Terminal-state integrity | Every row has exactly one of `reviewed`, `corrected`, or `unreadable`; no blank/model-defaulted/inferred status enters scoring. |
| E03 | Review provenance | CSV rows match frozen family/image hashes; suggestions remain distinct from human truth; unreadable rows are excluded from the accuracy denominator. |
| E04 | One sealed score | Run `scripts\run_anpr.py evaluate-ocr-test` only after E01-E03 pass and only once for this frozen test; retain the output artifact and exact hash. |
| E05 | OCR metrics | Record readable/unreadable counts, exact matches and denominator, full-string accuracy, Wilson 95% interval, character edits/characters and CER, nonempty coverage, and CPU mean/p95 latency. |
| E06 | OCR target | Label the 90% target `PASS` only if sealed full-string accuracy is at least 0.90; otherwise label it `FAIL`. Never substitute development accuracy. |
| E07 | Detector metrics | Confirm the unchanged frozen result: 36 images, 61 boxes, 52 TP, 3 FP, 9 FN, precision 0.9455, recall 0.8525, F1 0.8966 at confidence/IoU 0.50. |
| E08 | Metric separation | Presentation and audit distinguish plate-box detection, recognition on plate crops, and end-to-end scene ANPR; unmeasured end-to-end quality remains `UNVERIFIED`. |

## F. Runtime OCR and plate-search integration

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| F01 | Runtime OCR source | OCR predictions are generated from CityFlow runtime evidence under the frozen detector/OCR configuration, not copied from Indian benchmark truth. |
| F02 | Runtime OCR manifest | Manifest records code/config/model hashes, input journey/crop hashes, CPU/offline settings, counts, exclusions, failures, and timing. |
| F03 | Index integrity | Optional JSON index hash equals the config hash and its scenario/journey, OCR-selection, sealed-test, and runtime-manifest hashes all resolve exactly. |
| F04 | Evidence joins | Every index entry resolves to one current RoadEye ID, visit index, sample index, tracklet, camera, observation time, and crop SHA-256; duplicates and mismatches fail closed. |
| F05 | Search behavior | Exact, prefix, and contains queries normalize deterministically; ranking is exact then prefix then contains, then descending OCR score and stable evidence keys; limits are enforced. |
| F06 | Search failure behavior | Short queries, malformed schema, extra/prohibited fields, bad hashes, escaped paths, unknown journeys/evidence, and changed crops are rejected; disabled state returns zero results and an explicit reason. |
| F07 | Result semantics | Every result says `predicted_plate_text_not_ground_truth`; OCR score says uncalibrated/not probability; no owner or verification inference is returned. |
| F08 | Hybrid evidence | Selecting a plate result opens its existing journey and source evidence without changing association, merging identities, or treating OCR agreement as post-hoc ground truth. |

## G. API and frontend rehearsal

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| G01 | Required routes | Real HTTP returns expected status/content type for `/api/status`, `/api/vehicles`, `/api/vehicles/{id}`, crop, frame, `/api/analytics`, `/api/plate-search/status`, and `/api/plate-search`. |
| G02 | Error routes | Unknown ID/sample returns 404; invalid plate query returns 422 when search is enabled; malformed/tampered artifacts prevent startup. |
| G03 | Crop-to-journey moment | In a fresh browser, a real crop selects a chronological journey and renders matching crop/source frame, camera, timestamp, and link evidence. |
| G04 | Replay and map | Timed replay advances every visit; camera positions remain approximate; lines remain dashed/inferred; no tile request occurs. |
| G05 | Plate UI state | Before wiring it is visibly `BLOCKED` with disabled controls; after a valid index it is visibly `UNVERIFIED`, returns real predicted rows, and selecting one opens the linked journey. |
| G06 | S06 disclosure | S06 browser load keeps the no-ground-truth banner visible alongside every five-camera prediction and analytics panel. |
| G07 | Browser safety | CSP remains self-only; dynamic plate/result content uses DOM text fields rather than HTML injection; no external frontend asset is loaded. |

## H. Analytics and claim boundaries

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| H01 | Deterministic aggregates | Recomputed S06 summary equals 666 predicted IDs, 123 multi-camera IDs, 826 observed visits, and 160 predicted transitions from the pinned journey hash. |
| H02 | Aggregate isolation | Analytics uses runtime journeys/positions/link count only and contains no plate strings, global-ID listings, evaluator mapping, or owner data. |
| H03 | Terminology | UI/slides use “observed runtime visits,” “predicted endpoints,” and “transition support”; they do not claim density, verified OD, congestion, or route travel time. |
| H04 | Plate analytics | No plate-frequency, ownership, watchlist, or traffic claim is added unless separately approved and measured; current final audit expects none. |

## I. CPU timing and resource behavior

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| I01 | Measurement protocol | Record machine/runtime, warm-up, sample count, cold/warm distinction, mean, p50, p95, maximum, and failures; one-off values are labelled observations, not benchmarks. |
| I02 | Service startup | Measure cold S02 and S06 startup through completed hash validation and first successful `/api/status`. |
| I03 | API latency | Measure status, vehicle catalog/search, journey JSON, crop, decoded boxed frame, analytics, plate status, and enabled plate search. |
| I04 | Runtime OCR latency | Record detector, OCR, and combined per-evidence timings on the actual runtime batch plus exclusions/failures; do not reuse benchmark latency as runtime latency. |
| I05 | CPU/offline resource check | Confirm CPU device, no hidden download, bounded local memory/disk behavior, and successful operation without GPU or internet. |

## J. Final claims, documents, and handoff

| ID | Verification | PASS criterion and retained evidence |
|---|---|---|
| J01 | Presentation placeholder | Replace OCR placeholders only from E04 output; if E04 cannot run, keep every OCR test claim `UNVERIFIED`. |
| J02 | Claims cross-check | PRD, plan, architecture, audits, frontend copy, API notices, and presentation agree on two-camera verified, S06 five-camera unverified, detector metrics, OCR result, and analytics limitations. |
| J03 | Failure disclosure | Verified six-camera remains `FAIL`; any OCR target miss is `FAIL`; missing evidence remains `UNVERIFIED`; no result is hidden because it is unfavorable. |
| J04 | Final offline rehearsal | Execute the full live sequence from a clean server start using only documented commands and local assets; record screenshots/HTTP results as ignored artifacts and aggregate evidence in a tracked report. |
| J05 | Recovery/error rehearsal | Demonstrate clear behavior for missing/tampered runtime artifact, missing video/crop, bad journey ID, blocked OCR, and invalid/empty plate result. |
| J06 | Final audit report | Publish completed/verified/unverified/failed items, exact metrics/tests, files changed, deviations, timing, claim ledger, artifact hashes, latest local commit, and recommended next phase. |

## Stop/go rule

The final integrated audit may begin before plate search is enabled, but it cannot
close `PASS` as a whole while E01-E04 or F01-F04 are `UNVERIFIED`. If the review
CSV fails the 200-terminal/150-readable gate, do not score and do not build a
truth-derived workaround. Report the exact failure counts and return the file for
human correction. No final-audit item authorizes new Re-ID tuning.
