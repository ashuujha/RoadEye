# S06 demo prediction

**S06 — unverified prediction, no ground truth available**

This run uses the frozen S01/S03 selection without S06 tuning. It is not an accuracy result and does not change the verified six-camera FAIL status.

## Prediction summary

- Window: 0.0–199.9 seconds across 6 cameras.
- Baseline tracklets: 1674.
- Embedded tracklets: 826.
- Predicted links: 160.
- RoadEye global vehicle IDs: 666.
- Multi-camera predicted identities: 123.
- Maximum predicted camera span: 5.
- Identities at that span: 2.
- Accuracy metrics: none; S06 has no released ground truth.

## Maximum-span predictions

- `roadeye_c8392e4a29b15b95b2fb`: c044 → c043 → c045 → c042 → c041; min 0.707174, mean 0.781574, max 0.837488.
- `roadeye_ecd240ade37c5bf0984d`: c046 → c045 → c044 → c043 → c042; min 0.694447, mean 0.714413, max 0.772045.

Similarity values are uncalibrated cosine similarities, not probabilities.

## Run the local test interface

```powershell
.venv\Scripts\python.exe -m roadeye serve --config configs/demo-s06.json --host 127.0.0.1 --port 8000
```

The interface must continue to show: **S06 — unverified prediction, no ground truth available**
