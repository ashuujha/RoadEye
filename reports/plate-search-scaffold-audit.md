# Plate-search scaffold audit, hours 43-47

- Date: 2026-09-09
- Phase result: **PARTIAL** delivery; scaffold **PASS**, live OCR integration
  **UNVERIFIED**
- Starting commit: `399571f`
- Scope: API/index contract, disabled frontend state, presentation draft, and
  final-audit checklist only

## PASS

- **Prediction-linked index boundary:** `roadeye.plate_search` accepts an enabled
  index only from within the selected runtime-artifact directory and only when its
  configured SHA-256 matches. The index must bind the exact scenario and current
  `journeys.json` hash.
- **OCR provenance contract:** an enabled index must carry exact hashes for the OCR
  selection report, sealed OCR test report, and runtime OCR manifest. These are
  provenance references; benchmark strings are not accepted index fields.
- **Evidence joins:** every plate prediction must match an existing RoadEye global
  ID, visit/sample index, tracklet, camera, timestamp, and crop SHA-256. Duplicate
  evidence rows, unknown IDs, changed crops, escaped paths, malformed hashes, and
  extra fields fail closed.
- **Search behavior:** uppercase ASCII-alphanumeric normalization and deterministic
  exact/prefix/contains ranking are implemented. Results expose an existing journey
  and crop URL, use the label `predicted_plate_text_not_ground_truth`, and state
  that OCR scores are uncalibrated and not probabilities.
- **Blocked behavior:** both current configs explicitly declare
  `BLOCKED_PENDING_SEALED_OCR`. `/api/plate-search/status` reports the reason and
  `/api/plate-search` returns zero matches instead of fabricating or leaking a
  fallback value.
- **Frontend state:** the local test console renders a distinct plate-search panel.
  Input and submit controls remain disabled while blocked. The ready-path frontend
  can render predicted matches and open the already-existing journey without
  changing association.
- **Runtime isolation:** no ANPR transcription CSV, Indian benchmark truth,
  evaluator mapping, CityFlow identity, owner field, or production configuration
  was opened or added to a demo artifact. The required six prediction files remain
  unchanged; the optional future index is explicit and hash pinned.
- **Frozen Re-ID boundary:** no Re-ID source, model, association threshold,
  calibration, S02/S04/S05 output, or S06 prediction artifact was modified or
  regenerated.
- **Documentation:** the PRD, plan, architecture, and frontend README now distinguish
  completed scaffolding from pending runtime OCR wiring. A copy-ready presentation
  and exact hours 52-56 checklist were added.

## Measured verification

- `.venv\Scripts\python.exe --version`: **PASS**, Python 3.11.9.
- Focused plate/demo suite: **PASS**, 20 tests.
- Full repository suite: **PASS**, 91 tests in 14.06 seconds on the final rerun.
- `.venv\Scripts\python.exe -m ruff check .`: **PASS**.
- `.venv\Scripts\python.exe -m pip check`: **PASS**, no broken requirements.
- `node --check test_frontend\app.js`: **PASS**.
- Real S02 HTTP smoke: **PASS**; runtime integrity `PASS`, plate availability
  blocked, enabled false, and query result count zero.
- Real S06 HTTP smoke: **PASS**; runtime status `UNVERIFIED`, mandatory no-GT
  disclosure present, runtime integrity `PASS`, plate availability blocked, and
  query result count zero.
- Headless Edge S02 render: **PASS**; the `BLOCKED` chip, disabled input/button,
  exact sealed-OCR reason, 35-vehicle catalog, prediction analytics, selected
  three-camera journey, local map, and evidence timeline rendered together. The
  ignored screenshot is `artifacts/plate-search-scaffold-smoke-final.png`.

## FAIL

- **Sealed OCR readiness:** the latest tracked readiness evidence remains 0 reviewed,
  0 corrected, 0 unreadable, 200 missing, and 0/150 readable. This is the expected
  current gate and no scoring command was run.

## UNVERIFIED

- Sealed test full-string accuracy, Wilson interval, CER, runtime OCR latency, and
  the 90% target remain unverified.
- No CityFlow runtime OCR predictions or real plate index exist yet, so actual
  plate-query recall, precision, useful coverage, and plate/Re-ID hybrid benefit
  remain unverified.
- Recognition-on-crops is not end-to-end scene ANPR; end-to-end quality remains
  unverified.
- Astra 6/xhigh remains unverified because the host exposes no model/reasoning
  configuration. Plan Mode was unavailable because the host is in Default mode.

## Files changed in this checkpoint

- Runtime/API: `src/roadeye/plate_search.py`, `src/roadeye/demo.py`
- Config: `configs/demo.json`, `configs/demo-s06.json`
- Frontend: `test_frontend/index.html`, `test_frontend/app.js`,
  `test_frontend/styles.css`, `test_frontend/README.md`
- Tests: `tests/test_plate_search.py`, `tests/test_demo.py`
- Governing docs: `prd.md`, `plan.md`, `architecture.md`
- Handoff docs: `reports/final-demo-presentation.md`,
  `reports/final-integrated-audit-checklist.md`, this audit

## Remaining OCR wiring after the teammate handoff

1. Validate the replaced ignored CSV: exactly 200 terminal rows, zero missing or
   unrecognized statuses, and at least 150 readable rows.
2. Run the one sealed OCR test score and record every required metric even if the
   result misses 90%.
3. Run frozen detector/OCR inference over the chosen CityFlow runtime evidence on
   CPU/offline; write a manifest with source, model, code, input, exclusion, failure,
   output, and timing hashes/counts.
4. Emit the plate index defined in `roadeye.plate_search`, pin its exact hash in the
   chosen demo config, and prove every entry resolves to current journey evidence.
5. Re-run enabled API/browser/error smokes and then execute the hours 52-56 checklist.

No remaining step authorizes Re-ID retraining, threshold adjustment, or another
S02/S04/S05 tuning/evaluation pass.
