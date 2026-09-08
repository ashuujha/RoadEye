# Feasibility gate (2026-09-07)

## Environment — PASS

- `py -3.11` is available and reports Python 3.11.9. A `.venv` was created at `C:\RoadEye\.venv`.
- `pip` upgraded to 26.2.1 successfully.
- A stale pip process (PID 16176) was identified from its command line and stopped. `pip install --no-cache-dir -r requirements-cpu.txt` then completed successfully.
- Phase 33 re-verification passed editable install, `pip check`, and direct imports on Python 3.11.9. Tested versions include NumPy 1.26.4, OpenCV 4.11.0, Torch 2.4.1+cpu, torchvision 0.19.1+cpu, EasyOCR 1.7.2, and Ultralytics 8.3.0.

## CityFlow-V2 — PASS (hard gate)

- The archive is present and extracted under `data/cityflow/AICity22_Track1_MTMC_Tracking` after manual browser download. `ReadMe.txt` confirms 46 cameras, six scenarios, 880 annotated vehicles, synchronized videos, and train/validation MTMC ground truth.
- Contents include `cam_loc/` PNG camera maps, `cam_framenum/`, `cam_timestamp/`, per-camera `calibration.txt`, videos, `det/det_*.txt` baseline detections, `mtsc/mtsc_*.txt` baseline single-camera tracks, and `gt/gt.txt` in train/validation. Test contains no released GT, as expected.
- Parsing all 36 training GT files found 184 identity IDs. Identity **260** in scenario **S04** appears in **24 distinct cameras** (`c016`–`c039`). Validation’s maximum is 18 cameras (identity 398). Thus the verified archive-wide labeled maximum available locally is **24**, exceeding six.
- The shortest practical frozen demo window is scenario S04, identity 260, using the 24 camera tracklets and their synchronized `cam_timestamp/S04.txt` offsets. Candidate observations must be frozen from all S04 cameras in the selected interval before any association work.

The CityFlow hard gate is cleared. Do not commit the archive or extracted raw data. No Phase 2 work has started.

## Indian License Plates with Labels (Kaggle kedarsai) - PARTIAL PASS after Phase 33 re-audit

The archive downloaded successfully without credentials from the recorded Kaggle API URL. A complete extraction and extension-aware audit corrected the initial JPEG-only count:

- Archive size: **65,813,703 bytes** with **4,104 entries**: 2,021 YOLO `.txt` labels, 1,902 PNG plate crops, and 181 JPEG scene images.
- Decodable images: **2,083**. Paired with labels: **2,021**; 62 PNG files have no label.
- Supplied annotations remain **bounding boxes only**. There is no plate-string field or transcription file.
- Exact decoded-pixel grouping found **1,102 unique images** and 919 duplicate copies. The conservative split manifest contains **1,098 independent families** after scene pHash grouping.
- The frozen OCR benchmark capacity is **250 independent plate-crop representatives**: 50 development and 200 test. This meets the requested 150-300 test-image range once human strings exist.
- The frozen detection split contains 105 train, 36 development, and 36 test scene representatives.

**Capacity gate: PASS. Transcription availability: FAIL pending the user-approved manual workflow.** Bounding boxes never count as OCR truth. Phase 33 produced a development-only review tool; OCR scoring remains UNVERIFIED until 50 development plates are reviewed, preprocessing is frozen, and then 200 sealed test plates are reviewed. See `reports/anpr-data-audit.json` and `reports/anpr-transcription-runbook.md`.

## Supplementary checks — UNVERIFIED

- Thamizhsterio Kaggle API probe using the guessed endpoint returned HTTP 404; it was not downloaded. A manual Kaggle download may still work.
- The specified Roboflow project `yolov8-i4lu9` could not be verified within the one-hour supplementary-check budget; no files were downloaded.
- IEEE DataPort’s named dataset could not be verified or accessed in the capped check; no files were downloaded.

## Gate decision

| Gate | Status | Reason |
|---|---|---|
| CityFlow supports the planned real multi-camera journey | **PASS** | Real archive inspected; identity 260 spans 24 cameras in S04 with metadata, calibration, videos, baseline tracks, and released train GT. |
| Indian benchmark has enough independent images | **PASS** | Corrected audit found 200 frozen independent test crop families plus 50 development families. |
| Indian benchmark has usable plate strings | **FAIL** | The archive is box-only; human review is still required before OCR scoring. |
| Python CPU environment installs cleanly | **PASS** | Stale pip process stopped; no-cache install completed. |

Historical note: this report originally stopped before Phase 2. The user later approved the manual-transcription pivot and cleared Phase 2. CityFlow, Re-ID, and demo phases have since run. The current manual boundary is documented in `reports/anpr-audit.md`.
