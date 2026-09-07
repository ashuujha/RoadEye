# Private CityFlow Re-ID training runbook

## Inputs already prepared

- `artifacts/reid-training/roadeye-reid-training-data.zip`: 103,931,049 bytes, SHA-256 `93515f851d662fbb54c2bc5c5791f9c4b23f99b1f607f7648f09d2d01977abe6`.
- `artifacts/reid-training/roadeye-reid-colab-job.zip`: 19,608 bytes, SHA-256 `685a139f7581138707b8a03756a2c1af43a8157fe16cc87adb236fa7b6b32e89`.
- `notebooks/roadeye_reid_colab.ipynb`: the six-cell runner.

The data ZIP contains licensed CityFlow-derived crops and source identities. Keep it private; do not commit, publish, or redistribute it. The code ZIP has no data, weights, or credentials. The notebook verifies the code archive's internal file hashes before installation. The training loader then verifies the config, record file, and every crop hash.

## Manual Colab step

1. In your private Google Drive, create `MyDrive/RoadEye/`.
2. Upload both ZIP files listed above to that folder. No additional manual dataset or model download is required; the notebook explicitly downloads the pinned official VeRi initialization in Colab and checks its full SHA-256.
3. Open `notebooks/roadeye_reid_colab.ipynb` in Google Colab, select a GPU runtime, and run all cells in order. Do not make the notebook or Drive folder public.
4. Wait for `MyDrive/RoadEye/roadeye-reid-result.zip`. Download it to `artifacts/reid-training/returned/roadeye-reid-result.zip` in this repository.
5. Tell the coding agent that the result is present. Do not manually copy the model into a runtime config.

## Expected returned files

- `history.json`, with epoch zero plus 15 training epochs.
- `roadeye_cityflow_reid.pt`, containing only the versioned encoder payload.
- `roadeye_cityflow_reid.json`, containing hashes, split/training provenance, the epoch-zero baseline, selected development metrics, environment versions, and `evaluation_scenarios_used: []`.

## Acceptance after return

The next checkpoint must test the result ZIP, verify the manifest and full model hash, recompute the selected epoch from `history.json`, prove that no S02/S04/S05 evaluation scenario was used, load the artifact through `load_roadeye_encoder`, and run one CPU inference. Development mAP/rank-1 must be reported beside epoch zero; a non-improving result is a measured failure, not an improvement.

If development improves, freeze the model and association settings before one separately approved S02 evaluation. S04/S05 are already consumed and can only support disclosed post-hoc comparisons.
