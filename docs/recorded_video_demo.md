# Recorded-video vertical slice — SIH2026172

Actual local video → vehicle tracking → plate detection → crop OCR → PostgreSQL → console processing is implemented and verified below.

## Scope and source

One provided third-party recording, `data/recorded_real/delhi_anpr.mp4`, represents **REAL_C1 only**. Original source URL and redistribution permission are currently unknown; the original file is excluded from Git and is never modified or uploaded. Registry SHA256: `bef435656f050df576aedd5ac694824b9425a40b33072ef1213e377910cf1f96`.

PyAV decoded metadata: 1272 × 720, 25 FPS, 7,601 frames, 304.04 seconds, time base 1/12800, start PTS 0. The initial half-open interval is [0,60) seconds. Positions use decoded presentation timestamps. The default UTC anchor is **assigned** 2026-01-01T00:00:00Z, configurable per run; it is not the actual recording time. The burned-in timestamp/date/timezone are not interpreted.

## Models and decisions

All three models run locally with ONNX Runtime CPUExecutionProvider and two intra-op threads. This machine's NVIDIA driver is unavailable. Models are checksum-pinned in `packages/roadeye/recorded/models.json`; download URLs, export versions and sizes are stored there and snapshotted into each recorded run.

- Vehicle detector: Ultralytics YOLO11n COCO, [Espressif ONNX export](https://github.com/espressif/esp-dl/tree/master/models/coco_detect), export version 8.3.96. AGPL-3.0 model metadata. Six raw output tensors require DFL distance decoding and sigmoid class scores, following [Ultralytics source](https://github.com/ultralytics/ultralytics/blob/v8.3.96/ultralytics/utils/tal.py). Only car/motorcycle/bus/truck classes are retained.
- Plate-specific detector: [MorseTech YOLO11 license plate nano](https://huggingface.co/morsetechlab/yolov11-license-plate-detection), immutable revision 251a30d7daedca065f56e04b0af04052c907c68f, export 8.3.123, AGPL-3.0. Its author warns that upstream dataset overlap inflates benchmark results. No benchmark accuracy claim is adopted here.
- OCR: [fast-plate-ocr CCT XS global v2](https://github.com/ankandrew/fast-plate-ocr), 3.34 MB ONNX release. Repository MIT license; model weights stay outside this repository. The release config accepts RGB uint8 crops resized bilinearly to 128 × 64, ten character slots, Latin letters/digits and padding. India is not among the explicit region-head classes; regional generalization is unvalidated. Region predictions are not used. These upstream licenses do not establish permission to redistribute the recording.

Physical plate boxes are detected inside vehicle crops. The top 45 pixels are excluded before detection, and all crop coordinates are mapped back to the original frame. OCR never receives full frames or supplied strings. Lossless physical PNG crops (initial probe used JPEG), original frames, OCR slots/strings/character scores, bounding boxes, preprocessing and model hashes remain inspectable. JPEG evidence is an unannotated re-encoding of decoded pixels; the original MP4 remains unchanged.

Provisional passage rule: at 5 sampled frames/second, deterministic IoU association (threshold 0.15, maximum one-second gap) counts a vehicle once when its bounding-box bottom centre crosses y=300 downward after at least two detections. IDs are camera/run-local. Vehicles first appearing below the line do not count. Occlusion, detector misses and fragmented tracks can affect counts; this is not measured counting accuracy. Expensive plate/OCR inference runs selectively on nearby vehicle crops at least 0.6 seconds apart. Up to three largest score-weighted physical crops per track enter the existing consensus policy. Unreadable vehicles still publish passage inputs and rejected OCR outcomes.

The existing conservative AA00AA0000 normalizer remains unchanged; other plate shapes can be rejected even when raw text looks readable. Model scores are uncalibrated. Recognition accuracy is **unmeasured**, pending independent human labels.

## Durability

A recording request commits a run, immutable configuration/model/source snapshot, input event and outbox job before returning HTTP 202. The separate worker renews its fenced lease as progress commits. A crash retries decoding from the beginning with stable run/track/event IDs. Published passage/OCR receipts use the existing ingestion transactions, jobs, constraints and consensus. Duplicate inputs return original receipts; they do not add passages, observations or alerts. Original evidence is content-addressed, written before metadata receipt, and authorized through the existing evidence endpoint. Files left by a rolled-back receipt are possible orphans and can be reconciled with evidence metadata; do not delete the entire evidence store.

Synthetic camera lists, scenarios and controls remain scoped to the fictional network. Recorded runs reject synthetic trajectory/analytics endpoints and have separate recorded counts/status. No geographical placement, routes, speed or congestion is inferred for REAL_C1.

## Exact native startup and console steps

From the repository root, with Python 3.12, Node and a native PostgreSQL/PostGIS service:

```bash
make recorded-setup
export ROADEYE_RECORDED_ENABLED=true
# This session's existing native PostgreSQL service (preserved):
export ROADEYE_DATABASE_URL=postgresql+psycopg://roadeye@127.0.0.1:55432/roadeye
.venv/bin/alembic upgrade head
.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Second terminal, same two exported variables:

```bash
export ROADEYE_RECORDED_ENABLED=true
export ROADEYE_DATABASE_URL=postgresql+psycopg://roadeye@127.0.0.1:55432/roadeye
.venv/bin/python -m apps.worker.main
```

Third terminal:

```bash
cd apps/web
npm run dev -- --host 127.0.0.1
```

For another machine, replace the database URL with its own PostgreSQL/PostGIS URL; port 55432 and `/tmp/roadeye-pg` are session-specific native infrastructure, not a bundled database service. The normal Compose synthetic startup remains documented in README. Recorded processing was verified natively, not in Docker. Keep `ROADEYE_SOURCE_MODE=synthetic`: recorded capability is a separate explicit flag and each run carries its own immutable provenance. Use `ROADEYE_RECORDED_EVIDENCE_ROOT`/`ROADEYE_MODEL_ROOT` only in server configuration.

Open **http://localhost:5173**, sign in as administrator using the existing local password from ignored `.env`, select **Recorded video**, then **Process first 60 seconds**. The created run is selected automatically. Wait for **Processing: completed**. Click **Inspect passage** for a row; original crossing frame, plate crops, their supporting frames, raw strings and consensus are linked through authenticated evidence retrieval. Investigator can inspect; viewer and approver cannot inspect footage. No model credentials are in the frontend.

The original inference run retained for this handoff is `fe25474a-fa66-404d-9213-7013e3ca687f`. Select it in **Recorded run** to inspect without processing again. The separate synthetic run selector and fictional map do not appear in this view.

## Commands to repeat, review and extend

With the services running:

```bash
# Fresh isolated 60-second run (prints the new run ID):
.venv/bin/python -m scripts.recorded_video --seconds 60
# Durable progress and model/source configuration:
.venv/bin/python -m scripts.recorded_video --run fe25474a-fa66-404d-9213-7013e3ca687f
# Reprocess the SAME run; stable receipts retain original business effects:
.venv/bin/python -m scripts.recorded_video --run fe25474a-fa66-404d-9213-7013e3ca687f --replay
# Export a blank human-label table; contains sensitive local observations, so keep ignored:
.venv/bin/python -m scripts.recorded_video --run fe25474a-fa66-404d-9213-7013e3ca687f --export .runtime/recorded-review-new-export.csv
# After reviewing the initial results, process the whole clip in a NEW run:
.venv/bin/python -m scripts.recorded_video --seconds 304.04
```

Whole-clip processing is implemented through the same duration parameter but **has not been executed in this task**. The console intentionally starts only the first 60 seconds. A missing file, changed source/model digest, unavailable optional dependency or failed job is an explicit error; there is no mock fallback. A completed run's replay button is safe for duplicate demonstration. Failed runs may be retried after repairing the cause; active leases prevent an overlapping manual replay. A worker crash is automatically recovered after the configured lease expires (default 30 seconds).

The CSV contains passage/evidence IDs, clip time, machine output, and empty `human_plate`, `human_readability`, `human_notes` columns. Label using original pixels, preferably before exposing the machine string to annotators. CSV export does not change the database. For independent evaluation, use the new recorded evaluation form described below; operational observation corrections are a different workflow and must not be treated as ground truth. CSV edits are not automatically imported. Do not overwrite an existing labelled CSV.

## Measured results on this recording

The initial [0,60) interval was run through actual model inference and PostgreSQL, then repeated during crash/replay verification. CPU: Intel Core i5-12450HX, 12 logical CPUs; ONNX inference uses two intra-op threads, no usable NVIDIA driver. Python 3.12.13, PyAV 15.1.0, ONNX Runtime 1.22.1, OpenCV headless 4.11.0.86, NumPy 2.2.6. The lockfile records all dependencies.

| Measurement | Observed result |
|---|---:|
| Frames decoded in [0,60) | 1,500 |
| Frames sampled for vehicle inference | 300 (5 FPS) |
| Initial inference wall time | 25.064 seconds |
| Recovered run inference attempt | 25.301 seconds |
| Duplicate replay inference | 24.661 seconds |
| Counted downward crossings | 25 |
| Passages with retained plate detections | 22 |
| Accepted machine decisions | 2 |
| Review-required machine decisions | 6 |
| Rejected machine decisions | 17 |
| Pending machine outcomes after completion | 0 |
| Completed jobs per run | 51 (one video + 25 passage + 25 OCR) |
| Evidence objects retrieved and digest-validated on final run | 99 |
| Missing evidence on that verification | 0 |
| Unexpected processing failures on completed run | 0 |

The decoder reads a boundary frame at 60 seconds to terminate the half-open interval; the reported 1,500 count excludes that look-ahead frame. Wall times above measure each inference attempt, not queue wait, camera capture latency, or all HTTP/consensus processing. The complete forced-crash + lease wait + recovered attempt + duplicate replay + evidence verification took **84.614 seconds**. An intentional SIGKILL after three durable passage publications at 6.0 clip seconds was recovered with attempt count 2. Duplicate replay preserved all 25 passage IDs, all 25 observation IDs, outcome totals and 51 completed jobs. It is at-least-once processing, not an exactly-once-delivery claim.

Visual checks inspected original frames and crops from multiple passages, including the two-line bus plate at 6.8 seconds, a rejected nearby car at 1.0 seconds, unsupported-format crops at 21.6 and 44.2 seconds, and a blank-bodywork false plate detection around 34 seconds. A clearly readable nearby crop can still produce wrong OCR; the model is not validated for these conditions. Some correct-looking raw readings are rejected because the existing conservative plate format is unsupported or consensus has disagreeing frames. No manual characters were injected into inference or corrected to create a success example. **Recognition accuracy and counting accuracy are unmeasured.**

## Verification and remaining work

Run actual-model recovery acceptance with API running and **no other worker**; the script starts/kills/restarts its own workers:

```bash
export ROADEYE_RECORDED_ENABLED=true
export ROADEYE_DATABASE_URL=postgresql+psycopg://roadeye@127.0.0.1:55432/roadeye
.venv/bin/python -m scripts.recorded_acceptance
```

This creates another independent 60-second run and checks durable receipt/conflicts, partial-publication crash recovery, duplicate identities/totals, source isolation, ROI coordinates, every evidence asset and viewer denial. It now writes a run-specific ignored report to `.runtime/recorded-inspection/acceptance-<run-id>.json`; `--report <path>` selects an explicit path. Earlier `acceptance.json` artifacts remain historical reports. No OCR answers or ground-truth fixtures drive this check.

For browser checks, set `ROADEYE_RECORDED_RUN` to a completed actual run. CI skips that one footage-dependent test unless this variable is supplied; private footage and weights are not committed or automatically downloaded in CI. The ordinary synthetic browser and recorded permission tests run without footage. Hosted CI and Docker execution remain unverified in this environment.

Still required before operational use: source/redistribution authorization documentation, independent passage and plate labels, jurisdiction-appropriate normalization validation, evaluated OCR/plate detection for Indian and two-line plates, tracking/count accuracy evaluation, calibrated camera clocks and geometry, connected-camera footage, production identity/storage/retention controls, and actual target hardware benchmarking. The existing synthetic judge runbook remains unchanged and continues to demonstrate multi-camera trajectories; those trajectories are not claimed for this recording.

Additional independent source verification compared **all 39 retained lossless crops** with the exact decoded MP4 pixels at their stored PTS and bounding boxes: all matched. All **25 assigned observation timestamps** matched anchor + crossing-relative seconds. This checks pixel/time provenance independently of the OCR strings.

Final local regression checks: **39 Pytest tests passed** (15 unit,24 PostgreSQL integration), **one Vitest test passed**, backend Ruff/mypy and frontend TypeScript/build passed, generated OpenAPI/client consistency passed, the existing synthetic process E2E passed, and **all four Chromium checks passed** with the actual recorded run supplied. One upstream Starlette/AnyIO deprecation warning remains. During development, regressions caught and fixed an unfiltered REAL_C1 in synthetic analytics and a JPEG-only assertion after introducing lossless PNG evidence. These are resolved failures, not skipped checks.

The complete documented `make validate` target also passed with the native database, real recorded run and browser environment supplied. In this restricted workspace, use `UV_CACHE_DIR=/tmp/roadeye-uv` and `UV_PYTHON_INSTALL_DIR=/tmp/roadeye-python` for uv commands; the default home cache is not writable inside the sandbox. This is an environment prerequisite, not a substituted database/test.

`REAL_C1-L1` is a virtual counting corridor for this MVP, not a surveyed physical lane. The input quality/confidence multipliers remain neutral 1.0; they are not measured image quality or recognition accuracy. Detector/OCR raw scores and crop sizes are retained for inspection.

The final maintained acceptance script was rerun after adding the source-pixel assertions: run `d4cdcbca-c53a-4671-ab6c-0d86d88a921c`, 39 exact crop/PTS checks, 99 verified evidence objects, and all recovery/replay assertions passed in 86.44 seconds. The earlier reviewed run above remains available for the judge handoff.

## Independent human review after this audit

Audited 2026-09-05, baseline `ce06494`, delivered code `13759e8`. Use the native startup commands above; apply `.venv/bin/alembic upgrade head` before restarting the API. No new weights or dataset are needed on this machine. API, frontend and PostgreSQL suffice for reviewing completed runs; start the worker only when processing new/replayed inputs.

1. Open **http://localhost:5173** and sign in as **investigator** or **administrator** with the existing local password. Select **Recorded video**. Select original run `fe25474a-fa66-404d-9213-7013e3ca687f` in **Recorded run**. Do not press replay to begin labelling.
2. In **Independent human review**, use the source-video player and **Seek clip seconds** to inspect **all of [0,60)**. Use pause, seek increments of 0.04 seconds and the source frames. The count rule is a vehicle's detected bottom edge crossing y=300 downward in the 1272×720 original frame after at least two detections. REAL_C1-L1 is a virtual corridor. For human truth, count actual distinct downward crossings at that line; vehicles already below the line at interval start and vehicles that never cross it are outside this count definition. Do not equate this with all vehicles visible anywhere in the frame.
3. Before consulting OCR predictions, independently record the actual plate when fully readable from source pixels. Choose **Fully readable**, **Partially readable**, or **Unreadable**. The full transcription field starts blank and is enabled only for fully readable labels. Partial characters belong in notes; never guess missing characters. Use other nearby source frames to resolve readability; stop if it remains uncertain.
4. For each predicted row, click **Inspect passage**, then **View selected passage in source**. Inspect its crossing frame/vehicle box and all retained crop frames, plate boxes and lossless crops. Raw candidates/scores, normalization, contributions, reasons and model/policy metadata are available below. Older runs lack vehicle boxes at crop-frame times; their crossing vehicle box is shown only at the correct crossing frame. The source player supplies additional frames that were not retained as evidence.
5. Enter **Reviewer name**, **Vehicle assessment** (valid unique / duplicate / incorrect / not decided), **Plate detection assessment**, readability, independent transcription where justified, and notes. Click **Save passage evaluation**. The confirmation means the label was saved to PostgreSQL; it does not change the original observation. The local actor and self-reported name are retained. Repeat for **all 25 predictions**, including rejected and no-crop passages. Keep ambiguous cases undecided pending adjudication.
6. While surveying the source, identify any real crossing with no matching predicted passage. Pause at its time, set **Vehicle assessment** to valid, fill readability/notes, and click **Add missed vehicle at current time**. Create one marker per actual missed vehicle. Do not create a marker for an existing prediction merely because OCR failed. To revise/withdraw a marker, select it in **Missed marker to revise**, verify/seek its source time, enter the corrected assessment/notes and click **Revise selected missed marker**. Choosing incorrect withdraws it from the missed-vehicle count while preserving its revision history.
7. Only after reviewing the entire run interval and marking all missing crossings, check **I reviewed the entire run interval…**, enter your reviewer name, and click **Record timeline coverage**. Every unresolved vehicle/readability label still prevents complete recognition metrics. This declaration is an auditable human assertion, not automatic proof of recall.
8. Expand **Review coverage and explicitly defined metrics** and **Independent labels and revision identities**. `null` means not yet measured, not zero. Read the [metric definitions](recognition_error_analysis.md#metrics-available-after-human-review). Revised labels supersede earlier labels for calculations; earlier database rows remain immutable. The console shows latest labels; audit history records revision actions.
9. Independently inspect the separate v2 run `d7d83f8c-76ef-40fc-8c20-30c53f772ca9` for before/after comparison. Do not assume track IDs identify the same physical vehicle without checking source time/evidence. Do not copy inference results or treat adjacent video as an untouched evaluation split.

**Review state at handoff:** no real-run human labels were entered by the assistant. The existing CSV still has 25 unreviewed rows. Ground-truth count, recall, exact recognition accuracy and false accepts remain unmeasured. Automated tests create labels only on explicitly isolated test records, never on the Delhi evidence runs.

### Reproduce the audit without changing the original run

```bash
export ROADEYE_DATABASE_URL=postgresql+psycopg://roadeye@127.0.0.1:55432/roadeye
.venv/bin/python -m scripts.audit_recorded fe25474a-fa66-404d-9213-7013e3ca687f --output .runtime/audit/original-check.json
# API running, recorded enabled, no competing worker; creates a SEPARATE run:
export ROADEYE_RECORDED_ENABLED=true
.venv/bin/python -m scripts.recorded_acceptance --report .runtime/audit/new-check.json
```

The original audit reproduced 99 evidence digests, 39 exact source crops/OCR outputs and all 25 decisions. The v2 cadence fix retained 42 crops /102 verified evidence objects; 25 passages, 22 plate-proposal passages, **2 accepted /8 review /15 rejected /0 pending**. Recovered/replay inference attempts took 25.758/25.272 seconds on CPU. The full crash/replay check took 88.986 seconds. This is improved inspectability, **not measured improvement in recognition accuracy**. See [progress audit](progress_audit.md) for all executed checks and blocked Docker/GPU/hosted/labelled evaluation gates.

The first minute is now development data. Reserve a different interval as explained in [recognition analysis](recognition_error_analysis.md#development-and-evaluation-boundary); start-window support is not yet implemented. Whole-clip processing remains an available zero-based duration option, not an executed or untouched evaluation benchmark. Keep the original synthetic judge runbook: it demonstrates multi-camera rules using synthetic inputs; this one-camera recorded view demonstrates actual local inference only.
