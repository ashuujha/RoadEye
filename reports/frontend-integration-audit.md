# Frontend integration checkpoints (post-56h)

Scope: adapt Karman's UI to the audited read-only backend at ff3a618.
Backend source, model/evaluation artifacts, and the protected branches are unchanged.
Re-ID framing remains two cameras verified and the five-camera S06 demo unverified.

| Step | Built change | Verification |
| --- | --- | --- |
| 6.1 | Typed read-only client (fe58f7c) | Full frontend verification deferred |
| 6.2 | Reduced navigation (837934b) | Static checks recorded at checkpoint |
| 6.3 | Evidence workspace (d6074b0) | Static checks; tests pending |
| 6.4a | Trajectory and plate search (50ec830) | Static checks; tests pending |
| 6.4b | Analytics maps camera counts, OD endpoints, and transition-support proxies (f5d589d) | Static checks PASS; executable verification deferred |
| 6.4c | Typed camera map and prediction catalog; explicit interpolation only (e7eefd8) | Static checks PASS; executable verification deferred |
| 6.4d | Exact evidence drawer selection and /api proxy routing | Built; runtime/typecheck/tests/build UNVERIFIED until combined pass |

Analytics removes unsupported recognition coverage, privacy suppression, congestion,
travel-time and run-selection claims. Every aggregate is labelled UNVERIFIED and
prediction-only. Zero counts and negative boundary gaps are preserved; null time
bounds show unavailable. API failures never become zero-valued measurements.

No new zero-reference source files were identified at 6.4b. Tests are authored but
intentionally deferred until 6.4d, per user instruction. Graphify outputs remain
unstaged. Local checkpoint branches and verified all-ref bundles are created at
each sub-step; no push, browser rehearsal, or backend execution is authorized here.

6.4c removes the obsolete trajectory-to-map record adapter and consolidates map
geometry in NetworkMap. Camera projection preserves local aspect ratio, rejects
invalid coordinates, and shows omitted cameras explicitly. No connector is created
without a matching interpolation record. Zero and negative association boundary
gaps remain visible. Review/rejected layers and the hard-coded six-camera caption
are removed. No new dead source files were found.

6.4d replaces the /v1 observation drawer with read-only journey/sample resolution.
Plate search passes its exact visit index, sample index, and crop hash; neither a
missing sample nor a hash mismatch falls back to another crop. Map, trajectory,
and workspace selection open the same drawer. Source frames, complete crop hashes,
bounding boxes, timestamps, OCR and association score semantics remain visible.
Drawer Escape/Tab focus handling and image failure notices are implemented;
browser behavior remains UNVERIFIED until an authorized rehearsal.

Vite's development proxy changes from /v1 to /api as necessary client routing.
The frontend ignores installed dependencies and generated build/test output.
No new dead source files were found. Existing legacy tooling remains flagged:
the package's unused generate command targets the discarded OpenAPI schema and
would overwrite the audited typed client if invoked. It is not part of verification.
The openapi-fetch/openapi-typescript dependencies are also unused by runtime code.
No dependency or lockfile cleanup was included in these remap checkpoints.

Combined verification will install pinned frontend dependencies, run typecheck,
unit tests and production build, capture each exit code and full raw output, and
report all errors before any fix. No browser or backend test is part of this pass.
