# Final integrated audit, hours 52-56

- Date: 2026-09-09
- Phase start: `8f21a5e`
- Rehearsal-tooling checkpoint: `9c4dda4`
- Final package commit: reported in the handoff because a commit cannot contain
  its own ID
- Checklist: 63/63 items dispositioned
- Outcome: **60 PASS, 1 FAIL, 2 UNVERIFIED**
- Re-ID boundary: no training, threshold, association, or prediction change

The audit itself is complete. That does not mean every product target passed:
the verified six-camera result remains failed in the project claim ledger, and
the sealed OCR 90% target is the checklist's explicit `FAIL`.

## Checklist result

### A. Repository and environment

| ID | Result | Evidence |
|---|---|---|
| A01 | **PASS** | Phase start and implementation checkpoint recorded; all scoped files are locally committed at handoff; `git remote -v` is empty and no push occurred. |
| A02 | **PASS** | `.venv\Scripts\python.exe` is Python 3.11.9 and ran every Python command. |
| A03 | **PASS** | `pip check` found no broken requirements; CPU dependencies remain exactly pinned. |
| A04 | **PASS** | Integration suite: 95 passed in 12.94 s; final isolated rerun: 95 passed in 9.38 s. |
| A05 | **PASS** | Ruff and Node syntax checks passed. |
| A06 | **PASS** | `git ls-files` found no `data/`, `artifacts/`, CSV, weights, ZIP, database, crop, or review-page artifact. |
| A07 | **PASS** | User-owned `agents.md` and pre-existing Graphify worktree files remain unstaged; final files were staged explicitly. |

### B. Frozen inputs, provenance, and licenses

| ID | Result | Evidence |
|---|---|---|
| B01 | **PASS** | CityFlow path/window/source hashes resolve; S06 replay revalidated six baseline hashes plus metadata and prediction hashes. Local license PDF exists; derivative data remains private and ignored. |
| B02 | **UNVERIFIED** | Indian archive SHA-256, 1,098-family split, image hashes, review/test hashes, privacy rules, and no-redistribution behavior are recorded. An authoritative license identifier/terms snapshot is not preserved in tracked evidence, so license completeness is not passed. |
| B03 | **PASS** | Re-ID `1a7bdd...5cac`, detector `659814...3585`, and EasyOCR `e22726...29e8` match local files/manifests. Offline loading made no download. |
| B04 | **PASS** | `DemoRepository` constructed for S02/S06 only after prepared/run/journey/link/tracklet/topology hashes validated. |
| B05 | **PASS** | Runtime adapter allowlist remains the six prediction files plus explicitly configured, hash-pinned plate index and manifest. The manifest is an intentional integrity extension to the earlier index-only checklist wording. |
| B06 | **PASS** | Final presentation gives denominators, reports, scope, and limitations for every numeric detector/OCR/Re-ID/S06/analytics claim. |

### C. Ground-truth and data-boundary isolation

| ID | Result | Evidence |
|---|---|---|
| C01 | **PASS** | S02/S06 live servers ran under a `Path.open` guard rejecting `gt.txt`/`evaluation`; every required HTTP route still succeeded and responses exposed independent RoadEye IDs only. |
| C02 | **PASS** | Frozen journey/link files were not rewritten; S06 verify reused prepared inputs and reproduced prediction hashes. Plate integration wrote separate optional artifacts only. |
| C03 | **PASS** | Runtime builder imports no transcription loader and reports `benchmark_transcriptions_opened: false`; the CSV was used only by readiness and the single evaluator. |
| C04 | **PASS** | Exact-key index validation and source scan found no owner/person/address/watchlist/evaluator/benchmark truth field in index, API, or frontend. |
| C05 | **PASS** | Detector/OCR replay and runtime builds rejected Python network calls. Browser server logs show only localhost app/assets/API requests; CSP is self-only and no tiles/fonts/analytics load. Edge itself attempted vendor background services in its net log, so this finding applies to RoadEye page traffic, not the browser product. |
| C06 | **PASS** | Existing tests cover root containment and traversal rejection; index and manifest must stay inside the runtime artifact root. |

### D. Frozen vehicle journey evidence

| ID | Result | Evidence |
|---|---|---|
| D01 | **PASS** | Diff from `9fa2143` contains no Re-ID model, policy, S02/S04/S05 prediction, evaluator mapping, or threshold change. |
| D02 | **PASS** | `configs/demo.json` still selects frozen `artifacts/reid-trained-s02`. |
| D03 | **PASS** | Final copy states two cameras as the maximum fully scored consistent journey and discloses that 34/37 S02 links are unscored. |
| D04 | **PASS** | S06 verify reproduced assignment `b5d353...0198`, link `90a43f...e633`, decision `9ad207...55d`, and journey `ea6833...f0a0` hashes. |
| D05 | **PASS** | S06 remains five-camera predicted, no-GT and identity-accuracy `UNVERIFIED`; verified six-camera remains `FAIL`. |
| D06 | **PASS** | Live UI kept observed-visit, dashed interpolation, approximate-position, and uncalibrated-score labels. |

### E. Detector and sealed OCR evaluation

| ID | Result | Evidence |
|---|---|---|
| E01 | **PASS** | Readiness: 31 reviewed, 164 corrected, 5 unreadable, 0 missing, 0 unrecognized; 195 readable >=150. |
| E02 | **PASS** | All 200 rows were terminal; no inferred/default status entered scoring. |
| E03 | **PASS** | Family/image/split hashes were validated; unreadable rows were excluded; suggestions stayed distinct from reviewed truth. |
| E04 | **PASS** | `evaluate-ocr-test` ran once after readiness and created SHA-256 `ad2f70...9b23f`. It was not rerun during this audit. |
| E05 | **PASS** | 27/195 exact, 13.85%, Wilson 9.69-19.40%, 489/1,865 edits, 26.22% CER, 195/195 nonempty, 67.81/124.89 ms mean/p95. |
| E06 | **FAIL** | Frozen full-string accuracy is 13.85%, below the 90% target. |
| E07 | **PASS** | Frozen detector: 36 images/61 boxes, 52 TP, 3 FP, 9 FN, precision 0.9455, recall 0.8525, F1 0.8966 at confidence/IoU 0.50. |
| E08 | **PASS** | Presentation separates box detection, crop recognition, and unmeasured end-to-end scene ANPR. |

### F. Runtime OCR and plate-search integration

| ID | Result | Evidence |
|---|---|---|
| F01 | **PASS** | CPU builder used CityFlow journey crops, frozen threshold 0.50 and `color_upscale`; no Indian truth entered outputs. |
| F02 | **PASS** | Both manifests record source/crop-set/code/config/model hashes, CPU/network/seed settings, exclusions, failures, and stage timings. |
| F03 | **PASS** | S02 manifest/index `40e515...ff5` / `f08b19...be9`; S06 `ef4c02...ef4a` / `949e14...a5d5`; configs and embedded provenance resolve exactly. |
| F04 | **PASS** | Startup resolved every indexed row to current ID, visit/sample, tracklet, camera, timestamp, and crop hash; duplicate/mismatch tests fail closed. |
| F05 | **PASS** | Tests cover ASCII normalization and exact/prefix/contains ordering, descending score, stable keys, and limits. |
| F06 | **PASS** | Tests/live errors cover short query, extra field, bad hash, traversal, unknown evidence, changed crop, blocked state, and zero-match behavior. |
| F07 | **PASS** | Live responses use `predicted_plate_text_not_ground_truth`, `is_probability: false`, and uncalibrated-score notice. |
| F08 | **PASS** | Live handoff opened the result's exact journey/visit/sample/crop; journey JSON displays OCR beside appearance evidence without association change. |

### G. API and frontend rehearsal

| ID | Result | Evidence |
|---|---|---|
| G01 | **PASS** | Guarded real HTTP returned correct 200/content types for status, vehicles, journey, crop, decoded frame, analytics, plate status, and plate search in both configs. |
| G02 | **PASS** | Unknown ID/sample returned 404; short enabled query returned 422; tests reject tampered/malformed artifacts before startup. |
| G03 | **PASS** | Fresh headless-browser renders show selected chronological journeys, crops, camera/time evidence, source-frame path, and link evidence. |
| G04 | **UNVERIFIED** | Fresh renders verify local map, approximate points, and dashed geometry, but this audit did not automate a replay-button click. Earlier replay evidence exists; missing fresh interaction evidence is not promoted to PASS. |
| G05 | **PASS** | Fresh renders show `UNVERIFIED` enabled plate state and 1/2 indexed counts; live handoff and frontend code target the exact result visit/sample. |
| G06 | **PASS** | S06 fresh render visibly retains the no-ground-truth banner with the five-camera journey and unverified analytics. |
| G07 | **PASS** | CSP is self-only; dynamic result/plate content uses `textContent`; all RoadEye requests in server logs are local. |

### H. Analytics and claim boundaries

| ID | Result | Evidence |
|---|---|---|
| H01 | **PASS** | Pinned S06 analytics reproduce 666 IDs, 123 multi-camera IDs, 826 visits, and 160 transitions. |
| H02 | **PASS** | Aggregate report contains no plate strings, ID listings, evaluator mapping, owner data, or runtime truth. |
| H03 | **PASS** | UI/slides say observed visits, predicted endpoints, and transition support; traffic density, verified OD, congestion, and route-time claims are explicitly rejected. |
| H04 | **PASS** | No plate-frequency, ownership, watchlist, or traffic claim was added. |

### I. CPU timing and resource behavior

| ID | Result | Evidence |
|---|---|---|
| I01 | **PASS** | Machine/runtime, warm-up and sample counts, mean/p50/p95/max, wall time, failures, and observation-not-benchmark labels are recorded. |
| I02 | **PASS** | One-off repository construction through status: S02 221.84 ms, S06 45.71 ms; imports excluded and values are not benchmarks. |
| I03 | **PASS** | Five warm measured requests per route after one warm-up; table below records mean/p95. |
| I04 | **PASS** | Runtime manifests record detector/OCR/combined timing for 216 S02 and 849 S06 evidence crops plus all exclusions/failures. |
| I05 | **PASS** | Intel i5-1235U, torch 2.4.1+cpu, CUDA false; offline guards passed; four plate files total 8,661 bytes and no runtime failure occurred. |

### J. Final claims, documents, and handoff

| ID | Result | Evidence |
|---|---|---|
| J01 | **PASS** | Presentation placeholder was replaced only from the sealed report. |
| J02 | **PASS** | PRD, plan, architecture, runtime copy, audits, and presentation now agree on two-camera verified, S06 five-camera unverified, detector/OCR metrics, and analytics limits. |
| J03 | **PASS** | Six-camera and OCR target failures remain visible; missing license/replay evidence remains unverified. |
| J04 | **PASS** | Clean guarded S02/S06 server starts, real HTTP sequences, offline model replay, and fresh browser renders completed; ignored evidence is in `artifacts/final-audit/`. |
| J05 | **PASS** | Live bad-ID/sample/query behavior and tests for missing crop/video, blocked search, bad paths, and changed/tampered artifacts passed. |
| J06 | **PASS** | This report records completed/failed/unverified items, metrics, timings, hashes, deviations, changes, commits, and next-phase conditions. |

## Runtime observations

Machine: Windows 11 Home Single Language 64-bit, Intel Core i5-1235U (10 cores,
12 logical processors), approximately 16 GB RAM; Python 3.11.9, torch 2.4.1+cpu,
OpenCV 4.11.0, NumPy 1.26.4, CUDA unavailable.

Warm live HTTP latency, milliseconds (five requests after one warm-up):

| Route | S02 mean / p95 | S06 mean / p95 |
|---|---:|---:|
| Status | 13.85 / 30.43 | 15.98 / 17.56 |
| Vehicle catalog | 24.81 / 32.00 | 21.18 / 31.81 |
| Journey JSON | 15.49 / 29.77 | 15.98 / 19.60 |
| Crop | 11.47 / 24.87 | 19.50 / 32.61 |
| Decoded boxed frame endpoint | 197.94 / 233.51 | 97.59 / 109.45 |
| Analytics | 15.63 / 16.44 | 15.88 / 17.36 |
| Plate status | 2.58 / 2.93 | 16.25 / 27.41 |
| Plate search | 7.24 / 15.50 | 15.81 / 17.17 |

Runtime OCR was materially slower and sparse. S02 processed 216 crops in 34.11 s,
with detector mean 145.71 ms and OCR mean/p95 196.98/427.99 ms over seven attempts.
S06 processed 849 crops in 763.80 s, with detector mean 889.40 ms and OCR mean/p95
370.01/760.92 ms over 18 attempts. Only 1 S02 and 2 S06 strings were indexable.
Ultralytics assigned one shared detector timing to each result in a batch, so its
within-batch percentiles are identical; wall time is retained for context.

## Deviations and limitations

- Host model/reasoning settings are not exposed, so Astra 6/xhigh remains
  **UNVERIFIED**. The host stayed in Default mode; no Plan Mode claim is made.
- The accepted Re-ID training runtime used Python 3.13/torch 2.11 CUDA, while local
  CPU acceptance uses Python 3.11/torch 2.4. Exact training-code archive linkage
  remains **UNVERIFIED**; this is historical and was not changed here.
- The earlier checklist said optional index; runtime loading now also requires an
  exact-hash manifest. This narrows trust rather than expanding data access.
- Edge background services attempted vendor requests even with background-network
  flags. RoadEye's CSP, source, and server log show no page-initiated external
  request. Fully air-gapped browser-process behavior was not asserted.
- No independent time log exists, so exact adherence to 56 hands-on hours remains
  **UNVERIFIED**.

## Files and ignored evidence

Tracked phase files are the two audit-only scripts, this report, the updated plan
audit/checklist, and final presentation/status documentation. The preceding
`8f21a5e` checkpoint contains the sealed reports, runtime OCR/index builder,
plate-search API/frontend/config integration, tests, and architecture/PRD/plan
updates.

Ignored final evidence:

- `artifacts/final-audit/s02-http.json`, `s06-http.json`
- `artifacts/final-audit/s02.png`, `s06.png`, `s02-netlog.json`
- Both runtime directories' plate index and manifest
- The reviewed transcription CSV and model/prediction artifacts

## Completion decision

The approved 56-hour engineering and audit plan is **DONE**. Product success is
not a blanket pass: verified six-camera is **FAIL**, OCR 90% is **FAIL**, and the
claims listed above remain **UNVERIFIED**. The recommended action for the SIH
deadline is to freeze this package and present the honest two-camera verified,
five-camera S06 unverified, detector-box, weak sealed-OCR, sparse plate-search,
and prediction-analytics framing. Any accuracy improvement belongs to a new phase
with new development data and a new holdout.
