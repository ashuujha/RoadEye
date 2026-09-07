# Training-only Re-ID checkpoint audit — hours 21–24

## Completed

- Added deterministic, scenario-stratified, identity-disjoint S01/S03 splitting; private crop export; identity/camera-balanced training batches; cross-entropy plus batch-hard triplet optimization; development retrieval evaluation; epoch-zero comparison; best-epoch selection; and versioned model export.
- Added exact-hash loading of RoadEye-format encoders to the existing CPU embedding path. Runtime inference receives weights and provenance, not CityFlow identities or associations.
- Added a code-only Colab package and private notebook. The notebook verifies packaged source hashes, requires a GPU, explicitly downloads the full-hash-pinned VeRi initialization, and returns results through private Drive storage.
- Re-budgeted the fixed 56 hours so this three-hour portability checkpoint precedes the test frontend. No frontend, OCR, analytics, API, or association rewrite was started.

## Verified

- **PASS — source isolation:** the private bundle uses only `train/S01` and `train/S03`; 24 timestamp/GT/video source files were hashed. S02/S04/S05 do not appear. S02 remains untouched for a later frozen evaluation.
- **PASS — actual bundle:** 2,900 crops across 11 cameras and 113 identities; 2,318 crops/90 identities are training and 582 crops/23 identities are development. Identity overlap is 0, all 113 identities retain at least two cameras, and crop exclusions are 0.
- **PASS — bundle integrity:** the 2,902-member data ZIP passes `ZipFile.testzip`; `load_records` rechecked the records hash and all 2,900 image hashes. The archive is 103,931,049 bytes with SHA-256 `93515f851d662fbb54c2bc5c5791f9c4b23f99b1f607f7648f09d2d01977abe6`.
- **PASS — code package:** the 11-member code ZIP passes archive and internal source-hash checks. It is 19,608 bytes with SHA-256 `685a139f7581138707b8a03756a2c1af43a8157fe16cc87adb236fa7b6b32e89`; declared data, weights, and credential contents are all false.
- **PASS — CPU artifact contract:** the real FastReID architecture exported and reloaded through the production loader on Python 3.11.9 with torch 2.4.1+cpu. A `[1, 2048]` inference tensor matched exactly before/after serialization; maximum absolute difference was 0.0 and every loaded parameter was frozen. This is a portability check, not an accuracy result.
- **PASS — local validation:** 39 tests pass, Ruff passes for tracked source/tests/notebook, `pip check` reports no broken requirements, and all 22 config/report/notebook JSON files parse. The extracted code archive builds a wheel successfully through the normal isolated PEP 517 path, exposes the training CLI, and rejects CPU execution before creating output.

## Unverified

- **UNVERIFIED — GPU execution:** this machine has no CUDA device, so the 15-epoch job has not run.
- **UNVERIFIED — development accuracy:** no trained rank-1, mAP, loss curve, best epoch, or delta from epoch zero exists yet.
- **UNVERIFIED — returned trained artifact:** model hash/provenance and local CPU inference cannot be verified before the result ZIP is returned.
- **UNVERIFIED — S02 generalization and six-camera result:** S02 remains untouched. No post-training association or trajectory claim is made.

## Failed

- **FAIL — offline no-build-isolation packaging diagnostic:** the current venv has Setuptools 65.5 and no `wheel` package, so an intentionally offline `pip wheel --no-build-isolation` diagnostic cannot run `bdist_wheel`. The normal build-isolated package path used by the notebook passed. This is not a demo-startup dependency and training already requires an online Colab session for its explicit initialization download.
- The earlier frozen S05 result remains failed at the six-camera goal: 2/4 correct evaluable links, 2/647 pairwise recall, and two cameras in the longest fully scored consistent journey.

## Deviations and limitations

- The host exposed GPT-5, not the user-requested Astra 6 xhigh setting. The agent disclosed this before implementation and cannot change the host-selected model.
- The active environment imports OpenCV 4.11.0 because both `opencv-python` 4.11.0.86 and pinned `opencv-python-headless` 4.10.0.84 are installed. The bundle was built successfully, but this duplicate-package environment issue is not silently described as exact lockfile parity. Training does not import OpenCV.
- A first derived bundle was superseded after discovering that untouched validation scenario S02 should be declared as the future evaluation set. The final upload file and hashes in this audit refer only to the rebuilt archive; original CityFlow files were not changed.

## Checkpoint decision

Follow `reports/reid-training-runbook.md` to run the private GPU job and return its result. The next approved stretch should validate that returned artifact, report real development metrics against epoch zero, and freeze it before evaluating untouched S02. If the user defers GPU training, proceed to the hours 24–30 test-frontend phase with the documented two-camera limitation.
