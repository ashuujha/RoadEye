# U.S. CityFlow map routing audit

## Outcome

**PASS for the public map-preview objective.** The deployment fixture now serves eight pre-selected, frozen CityFlow V2 S02 prediction journeys at the published approximate U.S. scenario center instead of the former Delhi synthetic coordinates. The React map uses the authenticated production `/v1/map/cameras` and `/v1/map/trajectories` responses; there is no separate demo-route branch.

The deployment remains a metadata-only, read-only prediction preview. It includes no identity ground truth, source videos, crops, license plates, or model weights. All cross-camera identities and Re-ID scores must be described as **UNVERIFIED**.

## Frozen selection

| Rank | Vehicle ID | Camera sequence | Span | Minimum link score |
| ---: | --- | --- | ---: | ---: |
| 1 | `roadeye_5d01be7368ca57e9a2db` | c008 → c007 → c009 | 21.4 s | 0.850 |
| 2 | `roadeye_0e0b4f50a52b58ae9ec3` | c008 → c007 | 14.0 s | 0.927 |
| 3 | `roadeye_714071559a2b5ce2a24d` | c006 → c007 | 6.7 s | 0.852 |
| 4 | `roadeye_ab1e3b31f713579385c7` | c007 → c009 | 12.5 s | 0.875 |
| 5 | `roadeye_0d40f23565a857108d14` | c008 → c007 | 9.3 s | 0.865 |
| 6 | `roadeye_b9fe8f69ee2d5909bd57` | c006 → c007 | 9.3 s | 0.854 |
| 7 | `roadeye_5229ccd9991653beabda` | c007 → c009 | 24.8 s | 0.869 |
| 8 | `roadeye_e7134e2992dd5b3e8166` | c007 → c009 | 14.3 s | 0.907 |

The fixture builder verifies the four source-artifact hashes, all eight global IDs, their ordered camera sequences, required links, and required tracklets before writing deployable JSON. The output contains the original frozen journey/link/tracklet records and records the source hashes in `run.json`.

## Map interpretation

- Scenario center: `42.491916, -90.723723`, the approximate center published with CityFlow S02.
- Included cameras: c006, c007, c008, and c009, using the frozen calibration-derived positions.
- Lines connect successive camera observations chronologically. They are not GPS traces, surveyed camera coordinates, or road-snapped navigation routes.
- OpenStreetMap tiles require network access in the browser. The trajectory geometry and camera records still come from RoadEye's authenticated API.
- The highest-coverage three-camera journey is selected automatically as the lead example.

## Verification performed

- Focused Python API tests: 5 passed.
- React/Vitest tests: 12 passed.
- Production Vite build: passed.
- Ruff check of changed Python files: passed.
- Browser rehearsal against the local production data path: authentication, Live Map navigation, exact eight-ID ordering, alternate route selection, replay advancement, and 20 loaded OpenStreetMap tiles all passed with no page errors.

The complete Python suite was not claimed for this change; focused API and deployment-contract tests cover the modified backend behavior.
