# RoadEye test frontend

This plain HTML/JavaScript interface reads only frozen RoadEye runtime predictions
through the local FastAPI service. It does not read CityFlow identity labels and
does not contact a map, tile, model, or external analytics service.

From the repository root:

```powershell
.venv\Scripts\python.exe -m roadeye serve --config configs/demo.json --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Search by RoadEye ID, predicted tracklet, or camera;
select a crop; replay the predicted visits; and inspect every crop and boxed source
frame. The local aggregate panel shows prediction-only camera visits, OD endpoints,
and transition support with `UNVERIFIED` labels. Plate search is enabled over a
hash-bound runtime OCR index: search predicted text, then open the exact existing
journey visit and crop that produced it. Runtime coverage is sparse (one S02 entry
and two S06 entries), OCR scores are uncalibrated, and every string remains an
unverified prediction rather than plate truth. Benchmark transcriptions never
enter the demo.

The included Leaflet 1.9.4 files are locally bundled under its BSD-2-Clause
license. No basemap tiles are loaded. Camera points are approximate references
derived from CityFlow calibration, and dashed paths are straight interpolation.
