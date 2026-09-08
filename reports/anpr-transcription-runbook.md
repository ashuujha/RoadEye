# Indian plate transcription and OCR evaluation runbook

The Kaggle archive supplies plate boxes but no plate strings. Human review is therefore required before RoadEye can make any OCR accuracy claim. OCR suggestions are convenience text only and never become ground truth until a reviewer inspects every visible character and explicitly marks the row `reviewed`.

## Step 1: review development plates only

Open `artifacts/anpr/transcription-review.html` in Chrome or Edge. The page currently contains exactly 50 development families and no test images. For each plate:

1. Compare every character in the image with the text field. Correct the suggestion as needed.
2. Choose `reviewed` only when the complete string is legible. Choose `unreadable` when it is not possible to establish the full string.
3. Use **Mark reviewed + next** or `Ctrl+Enter` for a readable plate.
4. Export the CSV and replace `data/anpr/transcriptions.csv` with the exported file.

At least 40 of the 50 development families must have readable reviewed strings. Test rows must remain `suggested` or `pending` at this stage. The freeze command rejects premature test review.

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
predeclared benchmark floor. Then run the one test scoring command:

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
