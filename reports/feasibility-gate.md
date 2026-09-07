# Feasibility gate (2026-09-07)

## Environment — PASS

- `py -3.11` is available and reports Python 3.11.9. A `.venv` was created at `C:\RoadEye\.venv`.
- `pip` upgraded to 26.2.1 successfully.
- A stale pip process (PID 16176) was identified from its command line and stopped. `pip install --no-cache-dir -r requirements-cpu.txt` then completed successfully. Pinned packages, including Torch CPU and EasyOCR, are installed. Import verification is pending because the broad EasyOCR import command was interrupted while initializing; package installation itself is PASS.
- The initial invocation also produced a transient permission error invoking `.venv\Scripts\python.exe`; subsequent invocation worked. Retry is required before implementation.

## CityFlow-V2 — PASS (hard gate)

- The archive is present and extracted under `data/cityflow/AICity22_Track1_MTMC_Tracking` after manual browser download. `ReadMe.txt` confirms 46 cameras, six scenarios, 880 annotated vehicles, synchronized videos, and train/validation MTMC ground truth.
- Contents include `cam_loc/` PNG camera maps, `cam_framenum/`, `cam_timestamp/`, per-camera `calibration.txt`, videos, `det/det_*.txt` baseline detections, `mtsc/mtsc_*.txt` baseline single-camera tracks, and `gt/gt.txt` in train/validation. Test contains no released GT, as expected.
- Parsing all 36 training GT files found 184 identity IDs. Identity **260** in scenario **S04** appears in **24 distinct cameras** (`c016`–`c039`). Validation’s maximum is 18 cameras (identity 398). Thus the verified archive-wide labeled maximum available locally is **24**, exceeding six.
- The shortest practical frozen demo window is scenario S04, identity 260, using the 24 camera tracklets and their synchronized `cam_timestamp/S04.txt` offsets. Candidate observations must be frozen from all S04 cameras in the selected interval before any association work.

The CityFlow hard gate is cleared. Do not commit the archive or extracted raw data. No Phase 2 work has started.

## Indian License Plates with Labels (Kaggle kedarsai) — FAIL (hard gate)

The archive downloaded successfully without credentials:

- URL: `https://www.kaggle.com/api/v1/datasets/download/kedarsai/indian-license-plates-with-labels?datasetVersionNumber=1`
- Local archive size: **65,813,703 bytes**.
- Archive listing: **2,021 `.txt` labels** and **2,021 `.jpg` image paths** (4,104 entries including both sets).
- Extracted decodable image files: **181 `.jpg`** were present in this archive view.
- Sample label `labels/00000000.txt`: two YOLO rows containing class and normalized box coordinates only, e.g. `0 0.507305 0.174466 0.852273 0.242771`.
- No plate-string field, transcription file, OCR text, XML, CSV, or JSON was found in the archive listing. These are bounding-box annotations, not usable full-string OCR ground truth.

Achievable independent test size from the extracted image set is at most **181 before duplicate/near-duplicate review**, and therefore cannot meet the requested 150–300 target with a defensible held-out split plus development/training data. After de-duplication the number is **UNVERIFIED** until a review is performed. Manual transcription would be required, but transcription alone cannot make the current archive a sufficiently sized independent benchmark.

**Stopping rule triggered:** no usable transcriptions and no defensible benchmark capacity established. Do not silently substitute a dataset. User must decide whether to pivot to the thamizhsterio archive or another explicitly approved source.

## Supplementary checks — UNVERIFIED

- Thamizhsterio Kaggle API probe using the guessed endpoint returned HTTP 404; it was not downloaded. A manual Kaggle download may still work.
- The specified Roboflow project `yolov8-i4lu9` could not be verified within the one-hour supplementary-check budget; no files were downloaded.
- IEEE DataPort’s named dataset could not be verified or accessed in the capped check; no files were downloaded.

## Gate decision

| Gate | Status | Reason |
|---|---|---|
| CityFlow supports the planned real multi-camera journey | **PASS** | Real archive inspected; identity 260 spans 24 cameras in S04 with metadata, calibration, videos, baseline tracks, and released train GT. |
| Indian benchmark supports honest OCR evaluation | **FAIL** | Downloaded archive is box-only and exposes at most 181 images before de-duplication, with no transcriptions. |
| Python CPU environment installs cleanly | **PASS** | Stale pip process stopped; no-cache install completed. |

No Phase 2 work has started. The Indian OCR hard gate remains failed and requires the approved manual-transcription/supplementary-dataset decision. Await user clearance before proceeding to hours 10–18.
