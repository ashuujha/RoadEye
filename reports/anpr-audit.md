# Indian ANPR checkpoint audit (hours 33-43, manual review pending)

## PASS

- **Archive inventory and split freeze:** `data/indian-kedar.zip` contains 2,083 decodable images: 181 JPEG scenes and 1,902 PNG plate crops. There are 2,021 YOLO label files, 2,021 paired images, 328 scene boxes, and 1,840 crop boxes. The remaining 62 images have no label. The earlier feasibility count of 181 covered only JPEG files and is corrected here.
- **Duplicate isolation:** 919 exact pixel duplicate files were grouped before splitting. The manifest records 1,098 independent benchmark families. Plate-crop representatives are frozen as 50 development, 200 test, and 671 unused. Scene representatives are frozen as 105 train, 36 development, and 36 test. Hashes and family assignments are stored in `configs/anpr-split.json`.
- **Plate detector:** YOLOv8n was fine-tuned on 105 real scene representatives for 30 CPU epochs. Confidence 0.50 was selected using only 36 development scenes. One sealed 36-scene test run with 61 boxes measured 52 TP, 3 FP, and 9 FN: precision 0.9455 (Wilson 95% 0.8515-0.9813), recall 0.8525 (0.7428-0.9204), and F1 0.8966 at IoU 0.50. The exact best-weight SHA-256 is `6598143743e5edab23c9e9474f757dc4290310c3c45dce157dc7459235da3585`.
- **CPU OCR preparation:** EasyOCR's local recognition checkpoint is cached with SHA-256 `e2272681d9d67a04e2dff396b6e95077bc19001f8f6d3593c307b9852e1c29e8`. The final pre-freeze artifact runs color-upscale, CLAHE, and Otsu only over 50 development crops, producing 150 prediction rows. Suggestions remain unscored model output. Test inference is a separate post-freeze command using only the selected variant.
- **Offline integrity:** With Python socket and URL connection paths blocked, two development scenes and one development plate crop were inferred twice from cached models. Detector boxes and OCR text/scores matched exactly across replays.
- **Review isolation/UI:** The self-contained local review page renders in headless Chrome, passes `node --check`, contains exactly the 50 development images, and embeds zero test images. CSV export preserves all manifest rows. `freeze-ocr` rejects reviewed or unreadable test rows before it loads any transcription text.
- **Environment:** Python 3.11.9 editable install and `pip check` pass. Tested direct versions include NumPy 1.26.4, OpenCV 4.11.0, Torch 2.4.1+cpu, torchvision 0.19.1+cpu, EasyOCR 1.7.2, and Ultralytics 8.3.0. Both OpenCV distribution names are pinned to 4.11.0.86 because Ultralytics requires `opencv-python` while EasyOCR declares `opencv-python-headless`.

## UNVERIFIED

- **Sealed-test full-string OCR accuracy:** development has measured truth, but
  all 200 test rows still await human review. The pre-score audit measured
  `reviewed=0`, `corrected=0`, `unreadable=0`, `missing_status=200`, and
  `unrecognized_status=0`, then aborted. No test accuracy or 90% claim exists.
- **End-to-end scene ANPR:** the detector and recognition-on-supplied-crop tracks are evaluated separately. Detector output has not been fed into OCR for an end-to-end metric.
- **Near-duplicate visual review:** exact duplicates and conservative scene pHash families are grouped, but a human near-duplicate audit is unfinished.
- **Supplementary transcribed datasets:** the prior capped Roboflow and IEEE DataPort checks found no accessible plate-string corpus. No supplementary files were added.
- **Plate search and traffic analytics:** these remain in hours 43-47 and were not started in this checkpoint.
- **Astra 6/xhigh host setting:** repository instructions request this setting, but the host exposes no session control or model identity evidence. It remains unverified.

## Development OCR selection completed

The user reviewed all 50 development families: 48 were readable and two were
marked unreadable. The frozen `color_upscale` variant measured 10/48 exact full
strings, or **0.2083 accuracy** (Wilson 95% 0.1173-0.3426), with 106 character
edits over 459 ground-truth characters (**0.2309 CER**) and 48/48 nonempty
predictions. CLAHE also had 10/48 exact strings but a worse 0.2527 CER; Otsu had
9/48 exact strings and 0.3137 CER. These are development-selection measurements,
not test accuracy. They show that the current recognizer is far below the 90%
target on this development sample.

The selection report freezes the development prediction, model, split, config,
and runtime source hashes before test truth. A separate selected-variant inference
now covers 200 test families. The test-only review page passed headless Chrome and
JavaScript checks, embeds zero development images, and preserves all 250 CSV rows.
Test accuracy remains **UNVERIFIED** pending human review.

The review contract now has exactly three terminal values: `reviewed`,
`corrected`, and `unreadable`. Only the first two enter ground truth. The sealed
command writes `reports/anpr-ocr-test-readiness.json` and prints all status counts
before it can load truth. Missing or unrecognized values abort scoring; they are
never defaulted to reviewed. The current 200 model suggestions were migrated to
blank status while retaining suggestion text only as a review aid.

## FAIL

- **Six-camera verified journey:** unchanged. The post-hoc S05 prediction reaches five cameras, while its largest fully scored identity-consistent group reaches two. The frozen S02 demo prediction reaches three cameras. RoadEye must not present either as a verified six-camera journey.

## Deviations and failures encountered

- EasyOCR model preparation first hit a Windows CP1252 progress-bar encoding error. Setting its existing `verbose` option to false fixed the output path; the model was then downloaded explicitly.
- The first OCR inference passed a color array with `reformat=False` and failed shape unpacking. It was corrected to use EasyOCR's input reformatting and then completed all 750 predictions.
- Ultralytics downloaded a 755 KB Arial font during the explicit training command even though plots were disabled. This was not demo startup. Runtime was later replayed with networking blocked.
- The detector test was replayed after adding interval fields, without changing weights or threshold. Counts and accuracy metrics were identical; timing changed from 156.5 ms/image to 98.5 ms/image, demonstrating that this small batch timing is machine-load-sensitive. The report retains the latest measured run.
- The original review page and mixed prediction artifact included both development and test images. No rows were human reviewed, no test ground truth was scored, and no parameter was selected from test output. The mixed artifact was deleted and regenerated as development-only before handoff. The final workflow uses separate development/test prediction files, a development-only page, and an enforced test-sealing gate.
- The first post-freeze test-page build rejected every row because it still expected
  all three development variants. The unscored test prediction file and selection
  report were deleted, the review-only variant check was corrected, and the same
  development result was re-frozen under the new source hash. Test inference then
  ran again with only `color_upscale`; no test truth had been opened or scored.

## Checkpoint decision

Detector work is complete for this scope. Development OCR selection and sealed
test inference are complete, but Phase 33-43 cannot be called complete until a
human reviews the 200 test families and the one test scoring command runs. Follow
`reports/anpr-transcription-runbook.md`. Plate search and analytics remain in the
next phase.

## Verification commands

- `python -m ruff check .`: PASS.
- `python -m pytest -q`: PASS, 59 tests.
- `python -m pip check`: PASS, no broken requirements.
- `scripts/run_anpr.py verify-offline`: PASS with cached CPU weights and network guards.
- Headless Chrome review-page render and `node --check`: PASS; 50 development images, 250 preserved CSV rows, and zero embedded test images.
- `scripts/run_anpr.py freeze-ocr` before manual review: correctly rejected with `All development plate families require terminal review`.
- Post-freeze test page: PASS in headless Chrome; 200 test images, 250 preserved
  CSV rows, and zero embedded development images. Premature test scoring was
  correctly rejected with `All 200 test plate families require terminal review`.
