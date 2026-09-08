# Hours 27–33 audit — local evidence interface

## Completed

- **PASS — read-only API:** `roadeye.demo` loads the frozen S02 runtime directory,
  verifies the prepared manifest and prediction/evidence hashes, and serves vehicle
  catalog, journey, crop, and boxed source-frame endpoints.
- **PASS — runtime GT isolation:** the adapter has a fixed prediction-file allowlist
  and exposes no route for `evaluation/tracklet_gt_mapping.json` or CityFlow identity
  labels. It neither loads a model nor reruns association.
- **PASS — selection and evidence:** users can search a RoadEye ID, tracklet, or
  camera; select a real cached crop; and inspect all three causal appearance samples
  alongside exact source frames and predicted baseline boxes.
- **PASS — map and timeline:** locally bundled Leaflet renders approximate camera
  reference points, visit order, and dashed straight-line interpolation. Timeline
  cards show observed times and incoming appearance evidence.
- **PASS — browser load:** a headless Edge run loaded only local frontend/API assets
  and rendered a three-camera prediction, its timeline, crop, and source frame.
- **PASS — timed replay:** browser automation clicked replay and observed selection
  advance from step 1 (`c008`, 6.62 s), to step 2 (`c006`, 8.20 s), to step 3
  (`c009`, 10.66 s), then confirmed the control returned to its ready state.

## Measured integration results

- Runtime catalog: 1,503 RoadEye IDs, 35 multi-camera predictions, 37 links, and a
  maximum predicted span of three cameras.
- Search `c008/104` returned one result. The selected RoadEye prediction
  `roadeye_5d01be7368ca57e9a2db` replay data contains `c008 → c007 → c009`, with
  uncalibrated appearance similarities 0.9202885628 and 0.8504939079.
- HTTP smoke results: index/status/catalog/search/journey/crop/source-frame requests
  returned 200; a missing RoadEye ID returned 404. The tested crop was 19,342 bytes
  and the decoded annotated frame was 463,083 bytes.
- Single-request observations on this machine were 0.0304 s for the 35-row catalog,
  0.0119 s for the journey JSON, 0.0202 s for the crop, and 0.1326 s for source-frame
  decoding. These are one-run observations, not latency benchmarks.
- Validation: 7 focused tests and all 49 repository tests passed. JavaScript syntax,
  Ruff, dependency checks, 32 tracked JSON files, and real-artifact startup passed.

## Unverified or failed

- **FAIL — six-camera demo criterion:** unchanged. The frozen runtime maximum is
  three predicted cameras, while prior scoring verified at most two. The UI labels
  predictions and does not promote the three-camera result to verified truth.
- **UNVERIFIED — plate search and analytics:** intentionally deferred to hours
  33–47. No OCR claim or aggregate traffic claim is shown.

## Deviations and next work

Plan Mode was unavailable in the host session, so the phase used a bounded plan in
the working update. No scope or architecture deviation occurred. The next scheduled
checkpoint is hours 33–43: audit/deduplicate the available Indian data, build the
human transcription/review workflow, freeze an honest split, and implement/evaluate
CPU plate detection plus full-string OCR. It must retain bounding-box and string
ground truth as separate requirements.
