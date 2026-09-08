# ANPR sealed-test review triage audit

## Scope

This checkpoint adds a deterministic queue for the already-authorized manual
review of 200 sealed test plate-crop families. It does not score test OCR, change
the frozen OCR variant, or convert model suggestions into ground truth.

## Findings

- **PASS — frozen-input enforcement:** the builder verifies every hash recorded
  by `reports/anpr-ocr-selection.json` before reading test predictions.
- **PASS — complete prediction grid:** exactly one `color_upscale` prediction is
  required for every frozen representative test family.
- **PASS — ground-truth isolation:** ranking reads transcription provenance and
  status fields only. Plate strings do not influence the queue.
- **PASS — private output boundary:** detailed IDs, hashes, suggestions, and
  scores are written only below ignored `artifacts/anpr/` paths.
- **UNVERIFIED — sealed test OCR quality:** no metric is available until a human
  gives all 200 rows a terminal status and at least 150 are readable.

## Triage policy

Rows with an unrecognized status come first. Remaining unfinished rows are
sorted by ascending uncalibrated EasyOCR score, with the lowest relative quartile
labelled `manual_attention`, the middle half `standard`, and the highest relative
quartile `quick_check`. All rows still require explicit human inspection; these
labels are not probabilities, truth, or permission to auto-accept a suggestion.

## Commands

```powershell
.venv\Scripts\python.exe scripts\build_plate_review_triage.py
.venv\Scripts\python.exe scripts\run_anpr.py validate-ocr-test
```

The first command creates the ignored working queue. The second remains the
authoritative readiness gate before the one-time sealed OCR evaluation.

## Measured checkpoint

The builder verified 200/200 frozen test predictions and produced a 200-row
queue: 50 `manual_attention`, 100 `standard`, and 50 `quick_check`. No test row
currently has a terminal status, so readiness is **FAIL** with 0 readable rows
against the minimum of 150. The ignored JSON and CSV hashes are respectively
`b72e05f501f229f1c2034fea8bfb2bdc247c0f3c84f4a620b961aaf253cf5536` and
`42660f21679b3406260dd678972b14a8bf1ae89d330f8fa52d5b82a5e18f8c89`.

Targeted verification completed with 16 passing tests. OCR test accuracy remains
**UNVERIFIED**; this checkpoint generated no accuracy value and changed no review
status.
