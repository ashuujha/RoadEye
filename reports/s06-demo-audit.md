# S06 unseen-data demo audit

**S06 — unverified prediction, no ground truth available**

This audit is separate from the S02 verified and S04/S05 post-hoc evidence. No
S06 result is included in an accuracy metric or used to change the verified
six-camera criterion.

## Completed

- Froze the complete declared S06 interval, 0.0–199.9 seconds, across all six
  cameras (`c041` through `c046`) using public timing/frame metadata only.
- Loaded `mtsc_tnt_mask_rcnn.txt` baseline tracklets from each S06 camera.
- Bound the run to the already frozen S01/S03 association policy, pure trained
  Re-ID descriptor (`hsv_weight = 0.0`), and accepted model hash.
- Ran crop extraction, CPU embedding, causal association, independent RoadEye
  global-ID assignment, journey construction, and evidence export.
- Added an S06 test-interface configuration and a prominent UNVERIFIED banner.
- Kept all public S06 results in new S06-specific files. The existing
  `reports/reid-six-camera-repair-audit.md` and S02/S04/S05 outputs were not
  modified.

## Verified

- **PASS — six-camera input coverage:** all six declared S06 cameras were read
  for the full synchronized window.
- **PASS — frozen policy:** configuration values exactly match
  `reports/reid-six-camera-repair-selection.json`, SHA-256
  `c543dc6ec560894d5ba817b320e0f6456f18af4f7a51f2d9131ea3b706968d8c`.
- **PASS — frozen model:** SHA-256
  `1a7bddc94b065da1cc76f27f3455d61dc9752e687a87101c2eeb566353185cac`.
- **PASS — no retuning:** the S06 runner does not contain a selection or
  calibration step. It validates the frozen values before prediction.
- **PASS — no GT/scoring access:** the command ran under a fail-closed file
  guard that rejects `gt.txt` and any `evaluation/` path. No such file or
  directory exists in the S06 runtime output.
- **PASS — deterministic replay:** cached inputs reproduced identical hashes for
  assignments, links, decisions, and journeys.
- **PASS — local demo:** the real server returned HTTP 200 for status, vehicle
  list, the top five-camera journey, its crop, and its annotated source frame.
  The API status was `UNVERIFIED` and carried the required disclosure.

## Measured prediction results

These are prediction counts and uncalibrated cosine similarities. They are not
accuracy measurements or probabilities.

| Measure | Result |
|---|---:|
| Baseline S06 tracklets | 1,674 |
| Tracklets with valid three-crop prefixes and embeddings | 826 |
| Excluded tracklets | 848 |
| Predicted cross-camera links | 160 |
| RoadEye global vehicle IDs | 666 |
| Predicted multi-camera identities | 123 |
| Maximum predicted camera span | **5** |
| Identities at maximum span | **2** |

Predicted camera-span distribution: 543 one-camera, 91 two-camera, 29
three-camera, 1 four-camera, and 2 five-camera RoadEye identities.

| Unverified RoadEye ID | Cameras in predicted time order | Link similarity range | Mean |
|---|---|---:|---:|
| `roadeye_c8392e4a29b15b95b2fb` | c044 → c043 → c045 → c042 → c041 | 0.707174–0.837488 | 0.781574 |
| `roadeye_ecd240ade37c5bf0984d` | c046 → c045 → c044 → c043 → c042 | 0.694447–0.772045 | 0.714413 |

The JSON report records every incoming link for these two journeys, including
the selected similarity, second-best similarity, ambiguity margin, temporal
gap, topology distance, reason, decision time, crop hash, and source frame.

## Unverified

- **UNVERIFIED — every S06 identity/link:** S06 has no locally released ground
  truth, so correctness, precision, recall, and identity consistency cannot be
  measured.
- **UNVERIFIED — visual plausibility:** the interface exposes source evidence
  for human inspection, but that inspection is not a scored label.
- **UNVERIFIED — Astra 6/xhigh:** the host exposes no session-setting evidence.

## Failed

- **FAIL — verified six-camera criterion:** unchanged. The existing maximum
  fully verified, identity-consistent journey remains two cameras.
- **FAIL — S06 six-camera prediction:** the frozen policy reached five of six
  cameras, not six. This failure does not affect an accuracy score because no
  S06 score exists.

## Validation commands and results

- `.venv\Scripts\python.exe scripts\run_s06_demo.py verify` — PASS; all four
  prediction hashes reproduced exactly without GT or scoring access.
- `.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp-s06-final` —
  PASS; 68 tests passed in 3.65 seconds.
- `.venv\Scripts\python.exe -m pytest -q` — PASS on the final standard-command
  rerun; 68 tests passed in 3.72 seconds.
- `.venv\Scripts\python.exe -m ruff check .` — PASS.
- `.venv\Scripts\python.exe -m pip check` — PASS; no broken requirements.
- `node --check test_frontend\app.js` — PASS.
- `graphify update .` — PASS; 660 nodes, 1,414 edges, 38 communities.
- Real Uvicorn HTTP smoke on `127.0.0.1:8765` — PASS for status, vehicle,
  journey, crop, and source-frame endpoints.

One earlier full-suite attempt overlapped another pytest process on the shared
Windows temp directory. It reached 67 passing tests and one temp-cleanup setup
error. No application assertion failed. The isolated rerun above passed all 68
tests. An optional in-process `TestClient` smoke was skipped because the pinned
environment does not include its extra `httpx` dependency; the real Uvicorn
HTTP smoke covered the intended behavior without changing dependencies.

## Run the demonstration

```powershell
.venv\Scripts\python.exe -m roadeye serve --config configs/demo-s06.json --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`, select either five-camera RoadEye ID, and replay
the visits. Keep the yellow **S06 — unverified prediction, no ground truth
available** banner visible in every presentation.
