# Frontend browser rehearsal (post-56h)

Rehearsed source: 22ba094 (application changes through 70cbc7e).
Date: 2026-09-09 IST. Browser: Playwright Chromium 151.0.7922.34, headless.
Viewports: 1440x1000 desktop and 390x844 mobile.

Outcome: PASS for the exercised navigation, data rendering and exact plate-search
handoffs. FAIL for three display issues listed below. This is not an all-clear
visual audit. No application or backend fixes were made.

## Runtime used

Existing Python 3.11.9 demo servers loaded configs/demo.json (S02, port 8011)
and configs/demo-s06.json (S06, port 8012). Separate Vite servers used ports
5173 and 5174 with API_PROXY pointing to their matching localhost backend.
The browser sent actual requests through the frontend /api proxy. Responses
were not mocked. The existing backend and frozen runtime indexes were read;
benchmark transcription CSVs and evaluator mappings were not used.

This rehearsal exercises the development server and its API proxy. Production
deployment/hosting, other browser engines and physical mobile devices remain
UNVERIFIED. The previously passing production build was not changed or rerun.

## Route-by-route results

| Route | S02 rendered | S06 rendered | What did not render cleanly |
| --- | --- | --- | --- |
| Map | Four camera references; default three-visit prediction with two inferred connectors; 35 catalog options; visit drawer with crop and boxed frame | Six camera references; default five-visit prediction with four inferred connectors; 100 catalog options; visit drawer with crop and boxed frame | S06 boundary-gap labels overlap. No whole-page horizontal overflow at either tested viewport. |
| Trajectories | Ready index with one prediction; exact plate result, journey map, observed visits, association table and exact sample drawer; RoadEye-ID and no-match searches work | Ready index with two predictions; both exact plate results and their sample drawers work; RoadEye-ID and no-match searches work | Association table overflows the 390px viewport in both scenarios. Desktop fits. |
| Analytics | Four summary values: 1,503 predicted IDs, 35 multi-camera IDs, 1,540 runtime visits, 37 predicted transitions; tables have 4 camera, 12 OD and 12 transition rows | Four summary values: 666 predicted IDs, 123 multi-camera IDs, 826 runtime visits, 160 predicted transitions; tables have 6 camera, 18 OD and 17 transition rows | No rendering failure observed at the tested widths. Summary values and row counts match /api/analytics. |
| Evidence | 35 catalog cards; default journey has three visits and nine sample cards; all 18 crop/frame images decode; exact searched sample opens the shared drawer | 100 catalog cards; default journey has five visits and 15 sample cards; all 30 crop/frame images decode; exact searched sample opens the shared drawer | Long position-provenance text expands metadata cards beyond the viewport at both tested widths. |

The map is a static approximate camera diagram with inferred connectors, not a
street basemap or a continuous route. Its inferred-line checkbox successfully
hides/restores connectors. S06 catalog display is capped at 100 of the API's 123
multi-camera predictions; filtering is available. The default catalog is not an
exhaustive list of all 123 predictions.

Trajectory timeline previews show the first evidence sample of each visit. Those
previews can say no plate prediction even when the plate-search result refers to
sample index 2. Selecting that search result correctly opens the matched sample;
the preview itself does not switch to the matched OCR sample.

## Known indexed plate searches

Raw predicted strings and identifiers remain in ignored rehearsal evidence.
Case identifiers below follow the frozen index entry order.

| Case | UI search HTTP status | Returned / rendered results | Match | Selected evidence | Crop and boxed source frame |
| --- | --- | --- | --- | --- | --- |
| S02 entry 1 | 200 | 1 / 1 | exact | Visit index 0, sample index 2 | Both decoded; served crop bytes match indexed SHA-256 |
| S06 entry 1 | 200 | 1 / 1 | exact | Visit index 0, sample index 2 | Both decoded; served crop bytes match indexed SHA-256 |
| S06 entry 2 | 200 | 1 / 1 | exact | Visit index 0, sample index 2 | Both decoded; served crop bytes match indexed SHA-256 |

PASS: 3/3 known predicted strings returned results end to end through the UI.
Each click resolved the indexed RoadEye ID, visit, sample and crop hash.
None fell back to sample 0. OCR text and non-probability labels were present in
the drawers. This verifies search/evidence wiring, not OCR correctness.

PASS: map visit drawers and exact workspace-sample drawers also loaded.
Close-button initial focus, Shift+Tab/Tab containment and Escape closing passed
in the exercised desktop drawers. All 35 S02 and 100 displayed S06 catalog
thumbnails decoded after scrolling, as did all 48 crop/frame images belonging
to the two default selected journeys. Offscreen lazy images were explicitly
scrolled into view before this conclusion.

## Original display failures (repair results below)

1. **FAIL F01: S06 map gap-label collisions.** On the default five-camera
   prediction at 1440px, the labels for 21.50 s, 27.60 s and 13.00 s have three
   pairwise bounding-box intersections. The screenshot confirms the overlap.
   Camera points and all four inferred connectors render, but the colliding
   annotations are not cleanly readable. The S02 default has no such collision.
2. **FAIL F02: Trajectory association table exceeds mobile width.** At a
   390px viewport, S02 document width is 952px and S06 is 859px. The association
   table extends offscreen instead of remaining in a contained horizontal
   scroller. Search, journey rendering and drawer selection still work.
3. **FAIL F03: Evidence metadata exceeds desktop and mobile width.** Both
   scenarios produce a 1494px document at a 1440px viewport and a 468px document
   at a 390px viewport. The long approximate-position provenance string expands
   the metadata columns and is clipped/offscreen in the screenshots. Evidence
   images and API data are present.

The diagnostic's PASS counts indicate completed functional/data-collection
probes; they do not override these measured visual FAIL findings.

## Browser and network observations

- PASS: zero browser page exceptions, zero console errors/warnings and zero
  HTTP 4xx/5xx responses in the completed primary run.
- PASS: 91 S02 and 113 S06 browser /api requests were GET requests. No external
  HTTP requests were observed.
- Six net::ERR_ABORTED request cancellations per scenario were observed for
  status/catalog/analytics queries. Successful replacement requests supplied
  the rendered data. They are consistent with the development StrictMode and
  view-unmount cancellation paths, and were not HTTP failures.
- PASS: UNVERIFIED, predicted-identity/plate, approximate-position and
  non-probability notices remain visible. S06 explicitly discloses that no
  ground truth is available. The two-camera verified result and five-camera
  unverified S06 result were not re-evaluated or changed.

## Reproducibility and private evidence

Ignored diagnostic script: artifacts/frontend-rehearsal/rehearse.cjs.
It starts only its own local processes and terminates their process trees.
No application code is patched by the script.

Completed primary run (23 functional/data-collection probes):
artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/results.json.

Focused image/visual follow-up (eight probes):
artifacts/frontend-rehearsal/2026-09-08T22-12-08-450Z/results.json.

Evidence SHA-256:

- Current diagnostic script: ED3C041822EB3E1FF7CF867AD7C84CFD0A9BC1245A7672A27F443EEEC78A277A
- Completed primary results: 7F18AD14862DBB6BC2EE81075428CF7BB3296C71BDB69DFFD2B308C1C12B58E0
- Focused follow-up results: 7A64906C07629D336EBBE29DA7287CEA54F6239608BBD8544316E18186421B46

An earlier run under 2026-09-08T22-09-18-401Z was discarded after this
diagnostic assertion:

```text
Error: Drawer claim labels absent
```

It required the singular phrase "not a probability", while the no-OCR drawer
correctly rendered "not probabilities". That was a harness false failure, not
an application failure. The assertion and failed-probe drawer cleanup were
corrected only in the ignored script, then the completed primary run was made.
The initial run and its evidence remain preserved.

Selected screenshots (local ignored artifacts):

- [S02 map desktop](../artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/S02-map-desktop.png)
- [S06 map desktop and overlapping labels](../artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/S06-map-desktop.png)
- [S02 trajectory results](../artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/S02-plate-1-results.png)
- [S06 exact matched-sample drawer](../artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/S06-plate-2-drawer.png)
- [S06 analytics desktop](../artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/S06-analytics-desktop.png)
- [S06 analytics mobile](../artifacts/frontend-rehearsal/2026-09-08T22-10-19-365Z/S06-analytics-mobile.png)
- [S02 decoded evidence images](../artifacts/frontend-rehearsal/2026-09-08T22-12-08-450Z/S02-evidence-decoded-desktop.png)
- [S06 decoded evidence images](../artifacts/frontend-rehearsal/2026-09-08T22-12-08-450Z/S06-evidence-decoded-desktop.png)
- [Trajectory mobile overflow](../artifacts/frontend-rehearsal/2026-09-08T22-12-08-450Z/S02-trajectory-mobile-overflow.png)
- [Evidence mobile overflow](../artifacts/frontend-rehearsal/2026-09-08T22-12-08-450Z/S02-evidence-mobile-overflow.png)

## Handoff

### Layout repair 1: Trajectories (post-56h, 2026-09-09 IST)

PASS: four CSS declarations in style.css constrain the existing table panel,
enable horizontal scrolling, and let the ID/status row wrap. No JSX, API, data,
search, or evidence-selection changes. The first attempt reduced overflow to
471px but exposed the status-row overflow; that failure remains in private run
2026-09-08T22-22-02-693Z. The additional flex-wrap declaration fixed it.

Command: node artifacts/frontend-rehearsal/rehearse.cjs --route Trajectories.
Run: artifacts/frontend-rehearsal/2026-09-08T22-22-26-127Z/results.json.
Result: 11 PASS / 0 FAIL. S02/S06 desktop document widths are 1440/1440;
mobile widths are 390/390, replacing 952/859. Both association panels accept
horizontal scrolling. All three indexed plate searches return their exact
sample-2 crop and boxed frame; served crop bytes match the indexed SHA-256.
No HTTP errors, browser exceptions, or console errors. Only Trajectories was
rehearsed; the other two display failures are still pending at this checkpoint.
The ignored existing harness now filters routes and asserts width/scroll checks.
Its historical hash above describes the original rehearsal version.

### Layout repair 2: Evidence (post-56h, 2026-09-09 IST)

PASS: two CSS declarations on existing evidence-visit-metadata cells set
min-width: 0 and overflow-wrap: anywhere. Full provenance text remains visible;
no panel restructuring, JSX, API, or data changes. Desktop/mobile screenshots
were inspected and show wrapped text inside its existing cell.

Command: node artifacts/frontend-rehearsal/rehearse.cjs --route Evidence.
Run: artifacts/frontend-rehearsal/2026-09-08T22-23-19-526Z/results.json.
Result: 12 PASS / 0 FAIL. Both scenarios now measure 1440px at desktop and
390px at mobile, replacing 1494/468. All 18 S02 and 30 S06 default-journey
crop/frame images decoded, as did 35/100 displayed catalog thumbnails. Exact
sample-2 workspace drawers, crop-byte hashes, claim labels, and keyboard closing
passed. No HTTP errors, browser exceptions, or console errors in the route run.
Only Evidence was rehearsed. Map label repair is still pending here.
Previous layout checkpoint: 7451df1 (checkpoint/trajectory-layout-fixed).

### Original rehearsal handoff

All rehearsal server/browser processes were stopped. Application source,
backend source, configurations and frozen artifacts remain unchanged.
Only audit documentation is checkpointed; raw predictions, screenshots and
runtime logs remain ignored. No push, merge or remote changes occurred.

Recommended next work is a narrowly scoped frontend display repair for F01-F03,
followed by focused browser checks. It has not been executed; results are
returned for user review before any discussion of publishing branches.
