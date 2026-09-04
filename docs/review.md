# Final engineering review

Review basis: this specification, repository code, official uv integration documentation, executed PostgreSQL/process/browser tests. No attached handbook was available; no prior project code or claims were imported.

## Concrete findings and fixes

| Finding | Correction | Evidence |
|---|---|---|
| Invalid GET time windows could raise uncaught model errors | Common validation error handler | Invalid-window integration assertion |
| Concurrent first seed could conflict | Transaction-scoped advisory lock | Concurrent command/input tests plus constraints |
| Receipt stored only evidence key until processing | Persist evidence metadata atomically with input/job; reject changed content per key | Rollback and pending-receipt metadata test |
| Application-only provenance immutability was insufficient | Database triggers protect raw input, machine decisions, audit and run scope/graph | Direct prohibited SQL update tests |
| Snapshot freshness could be mistaken for window uptime | Separate union-of-heartbeat-interval coverage fields and limitations | Exact 240 s interval-union assertion |
| Generic envelopes offered weak client contract checking | Explicit run/observation/journey/analytics/alert response schemas | Schema generation, TypeScript and actual API validation |
| Initial frontend tooling had known advisories | Pinned patched Vite/Vitest/Playwright | npm audit reported zero vulnerabilities after update |
| Container node user could lack cache write permission | Set ownership before switching user | Code inspection; Docker runtime still blocked |
| Generated lock tooling was newer than proposed CI tool | Pin uv 0.12.1 to locally exercised version | Locked offline sync succeeded; official integration consulted |
| Native database returned timestamps in its local timezone | Force UTC sessions and UTC serialization/window normalization | UTC output asserted in late-input test |
| Native PostgreSQL template used SQL_ASCII | Clean-test database explicitly uses UTF8/template0 | Independent clean migration/PostGIS test passed |

## Trace checks

Inputs → PostgreSQL input/evidence/job transaction → leased worker → passage/OCR/observation → query/analytics/alert → typed API → polling console. Ground truth is read only by tests/generator, not application processing. No mock-response backend, hard-coded journey output or chart series generates results. The console's fixed default query plate/time merely selects input scope.

Duplicate-event and command keys compare payload digests; run/camera/passage and observation uniqueness prevent duplicated effects. Leases are durably committed and stale tokens rejected. Domain effects/job completion share a transaction. Tests cover rollback, retry, poison, lease reclamation, worker restart and full database restart evidence.

All queries bind run scope; revisions preserve raw machine output; graph snapshots isolate later configuration edits. Counting reads passages, not OCR outcomes. Ambiguous links remain visible and are excluded from definite flow. Server-enforced roles protect searches/evidence/actions; browser permission-denied states were exercised.

Remaining boundaries are in `limitations.md`: production identity, streaming real inference, retention/cleanup, city-scale capacity, general network provisioning, Docker startup and hosted CI execution. These are not claimed delivered or validated. No recognition-accuracy percentage is reported.
