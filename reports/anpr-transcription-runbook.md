# Indian plate transcription and OCR evaluation runbook

The Kaggle archive supplies plate boxes but no plate strings. Human review is therefore required before RoadEye can make any OCR accuracy claim. OCR suggestions are convenience text only. The only terminal status values are `reviewed`, `corrected`, and `unreadable`; only the first two become ground truth after a reviewer inspects every visible character. Blank or unrecognized values are never truth.

**Current state:** development review is complete and `color_upscale` is frozen.
The page now contains the 200 sealed test families. Continue at Step 2; do not
rerun development selection or change tracked ANPR source/configuration.

## Step 1: review development plates only

Open `artifacts/anpr/transcription-review.html` in Chrome or Edge. The page currently contains exactly 50 development families and no test images. For each plate:

1. Compare every character in the image with the text field. Correct the suggestion as needed.
2. Choose `reviewed` when the suggestion was already exact, `corrected` when you changed it, or `unreadable` when it is not possible to establish the full string.
3. Use **Mark reviewed + next**, **Mark corrected + next**, or `Ctrl+Enter` for an unchanged reviewed plate.
4. Export the CSV and replace `data/anpr/transcriptions.csv` with the exported file.

At least 40 of the 50 development families must have readable `reviewed` or `corrected` strings. Test rows must have blank status at this stage. The freeze command rejects premature test review.

Run:

```powershell
.venv\Scripts\python.exe scripts\run_anpr.py evaluate
.venv\Scripts\python.exe scripts\run_anpr.py freeze-ocr
```

The first command measures all three preprocessing variants on development truth. The second freezes one variant by full-string accuracy, then character error rate, latency, and a stable name tie-breaker. It writes `reports/anpr-ocr-selection.json` with hashes for the split, predictions, model, configuration, and source.

## Step 2: review the sealed test plates

After `freeze-ocr` succeeds, rebuild the page:

```powershell
.venv\Scripts\python.exe scripts\run_anpr.py predict
.venv\Scripts\python.exe scripts\run_anpr.py build-review
```

The first command runs only the frozen preprocessing variant and writes a separate
test prediction file. The page will then contain exactly 200 independent test
families. Review them with the same rules, export the CSV, and replace
`data/anpr/transcriptions.csv`. At least 150 must be fully readable to meet the
predeclared benchmark floor. Validate and inspect the exact status counts first:

```powershell
.venv\Scripts\python.exe scripts\build_plate_review_triage.py
.venv\Scripts\python.exe scripts\run_anpr.py validate-ocr-test
```

The triage command verifies the frozen OCR selection and exact 200-row prediction
grid, then writes private ignored JSON/CSV queues under `artifacts/anpr/`. It puts
invalid statuses first and otherwise orders pending rows by the uncalibrated OCR
score, lowest first. This is a review-order convenience only: suggestions are not
truth, every test family still requires a terminal human decision, and the order
does not change the scoring denominator.

The command reports `reviewed`, `corrected`, `unreadable`, `missing_status`, and
`unrecognized_status`. It aborts unless every test row has an allowed terminal
status and `reviewed + corrected >= 150`. Then run the one test scoring command:

```powershell
.venv\Scripts\python.exe scripts\run_anpr.py evaluate-ocr-test
```

The report contains the actual full-string accuracy with a Wilson 95% interval, character error rate, coverage, and CPU latency. A result below 90% remains the result. This benchmark measures recognition on supplied plate crops; it does not establish end-to-end scene ANPR accuracy or city-wide performance.

## Rebuild and integrity commands

The ignored page and predictions can be rebuilt from tracked manifests and local ignored data/models:

```powershell
.venv\Scripts\python.exe scripts\run_anpr.py predict
.venv\Scripts\python.exe scripts\run_anpr.py build-review
.venv\Scripts\python.exe scripts\run_anpr.py verify-offline
```

Do not commit the transcription CSV, review page, images, predictions, or model weights. They remain under ignored `data/` and `artifacts/` paths.
