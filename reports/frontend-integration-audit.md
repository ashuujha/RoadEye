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
| 6.4b | Analytics maps camera counts, OD endpoints, and transition-support proxies | Built; runtime/typecheck/tests/build UNVERIFIED until combined pass |
| 6.4c | Network map | Pending |
| 6.4d | Evidence drawer and selection handoff | Pending |

Analytics removes unsupported recognition coverage, privacy suppression, congestion,
travel-time and run-selection claims. Every aggregate is labelled UNVERIFIED and
prediction-only. Zero counts and negative boundary gaps are preserved; null time
bounds show unavailable. API failures never become zero-valued measurements.

No new zero-reference source files were identified at 6.4b. Tests are authored but
intentionally deferred until 6.4d, per user instruction. Graphify outputs remain
unstaged. Local checkpoint branches and verified all-ref bundles are created at
each sub-step; no push, browser rehearsal, or backend execution is authorized here.
