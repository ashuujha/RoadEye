# Frontend integration checkpoints (post-56h)

Scope: adapt Karman's UI to the audited read-only backend at ff3a618.
Backend source, model/evaluation artifacts, and the protected branches are unchanged.
Re-ID framing remains two cameras verified and the five-camera S06 demo unverified.

| Step | Built change | Verification |
| --- | --- | --- |
| 6.1 | Typed read-only client (fe58f7c) | Included in passing combined typecheck/build; browser UNVERIFIED |
| 6.2 | Reduced navigation (837934b) | Included in passing combined typecheck/build; browser UNVERIFIED |
| 6.3 | Evidence workspace (d6074b0) | Component test PASS; browser UNVERIFIED |
| 6.4a | Trajectory and plate search (50ec830) | Component/geometry tests PASS; browser UNVERIFIED |
| 6.4b | Analytics maps camera counts, OD endpoints, and transition-support proxies (f5d589d) | Static checks and claim-boundary tests PASS; browser UNVERIFIED |
| 6.4c | Typed camera map and prediction catalog; explicit interpolation only (e7eefd8) | Static checks, geometry and claim-boundary tests PASS; browser UNVERIFIED |
| 6.4d | Exact evidence drawer selection and /api proxy routing (70cbc7e) | Selection/validation/render tests PASS; browser UNVERIFIED |

Analytics removes unsupported recognition coverage, privacy suppression, congestion,
travel-time and run-selection claims. Every aggregate is labelled UNVERIFIED and
prediction-only. Zero counts and negative boundary gaps are preserved; null time
bounds show unavailable. API failures never become zero-valued measurements.

No new zero-reference source files were identified at 6.4b. Tests were
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

## Combined verification result

PASS on the first pass at source commit 70cbc7e. Node v24.20.0 / npm 11.19.0.
Full raw output: [frontend-integration-verification-70cbc7e.txt](frontend-integration-verification-70cbc7e.txt).

| Command (apps/web) | Exit | Result |
| --- | --- | --- |
| npm.cmd ci --no-audit --no-fund | 0 | PASS: 136 packages installed |
| npm.cmd run typecheck | 0 | PASS: no diagnostics |
| npm.cmd test | 0 | PASS: 19 tests in six files |
| npm.cmd run build | 0 | PASS: TypeScript build and Vite production bundle |

No errors, fixes, retries or dependency-version changes occurred. npm warned that
esbuild@0.25.12 has a postinstall script not yet covered by allowScripts. The warning
was reported verbatim before proceeding; no script approval was changed, and the
production build succeeded. Package and lockfile are unchanged.

Build output (ignored):

| Asset | Size | SHA-256 |
| --- | --- | --- |
| dist/index.html | 0.38 kB | 92D8ED3F1B704F82D9A2945BD4C983C9E2AAC82995270ED8824D2C9D4D65CBDB |
| dist/assets/index-CMBSYyu5.css | 33.69 kB | 7DEA6D20F66F4CD7BD7DA535035C40D6761078403EC1B269E06D6BD1AD2F2D31 |
| dist/assets/index-CJGGkMH2.js | 277.59 kB | F4CD6C7DBC288664DF9AC73B71552833C70C7C8D951E93E5833EE56D039202F9 |

## Local backup checkpoints

All bundles below are under C:\RoadEye-backups\pre-integration-ff3a618.
Each verified as a complete-history all-ref Git bundle.

| Step | Local checkpoint branch | Bundle | SHA-256 |
| --- | --- | --- | --- |
| 6.4b | checkpoint/audited-analytics | RoadEye-after-analytics.bundle | 50D103F6132956A86F9692A2AA0C7B9423A98D1F8BA11B02DA9AFE236FE6A9C8 |
| 6.4c | checkpoint/audited-network-map | RoadEye-after-network-map.bundle | 17C5A2380842B9DD873CE9F82DC01AF4E7A07F53E9B21F7793AA03632EDF9BD0 |
| 6.4d | checkpoint/audited-evidence-drawer | RoadEye-after-evidence-drawer.bundle | 0FD62874B177E98387AA100E5FF45CC026F3AB9FC58272AAE0B395D1FF5F713F |

## Remaining verification and scope

- UNVERIFIED: browser interactions, responsive appearance, keyboard focus behavior,
  live API proxy requests and image loading. No browser rehearsal was run.
- Backend/Re-ID/OCR metrics were not re-evaluated or changed. The backend source,
  configs, scripts, tests and original test_frontend have no diff against ff3a618.
- PASS: master, backend-audited and backup-before-cleanup still point to ff3a618.
  No remote was configured or changed, and nothing was pushed.
- PASS: final import scan found zero unreferenced non-entry source files.
  Legacy unused generation tooling is flagged above; it was not invoked.
- Next phase: user review, then an explicitly authorized browser/API rehearsal.
  Production hosting/serving of the built React assets remains outside this pass.
