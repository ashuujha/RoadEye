# RoadEye requirements — SIH2026172

Bharat Electronics Limited problem: inspect city-wide ANPR sightings, plausible camera journeys and traffic patterns. Users are investigators, traffic analysts, administrators and separate watchlist approvers. This repository implements a local engineering demonstration with synthetic multi-camera scenarios and optional actual recognition from one recorded camera; recognition accuracy is not measured.

## Scope and acceptance

| ID | Requirement | Acceptance / verification |
|---|---|---|
| R01 | Durable ingestion | Atomic input/job receipt; concurrent retries produce one passage; PostgreSQL integration |
| R02 | Passage/recognition separation | Unreadable passage increases count without accepted recognition; scenario integration |
| R03 | Conservative consensus | Retain raw candidates, frame deduplication, explicit reasons and policy; unit tests |
| R04 | Constrained journeys | Directed graph, hard travel constraints, alternatives and collision rejection; unit/integration |
| R05 | Analytics | Half-open event-time counts reconcile to passages, bounded journey-derived flow; integration |
| R06 | Watchlists/review | Distinct creator/approver, valid scoped matches, suppression, audit; integration |
| R07 | Recovery/replay | Leases, retry, poison state, idempotent processing; integration |
| R08 | Access/evidence | Server role checks, hashed local sessions, authorized evidence, safe keys; API integration |
| R09 | Console | Real API data, synthetic labels, loading/empty/error/stale states; browser smoke |
| R10 | Provenance/versioning | Immutable synthetic runs, separate receipt/capture/process times; late events change versions; integration |

Investigator journey: sign in, select a synthetic run, process inputs, inspect consensus, query a plate, inspect alternatives and evidence, review uncertainty. Administrator journey: configure network, run/pause/step/replay scenarios, inspect processing failures. Approver journey: approve another actor's watchlist draft. Viewer journey: inspect aggregate coverage and processing health without plate access.

## Boundaries

MVP: one fictional network with supplied mock OCR candidates, bounded query reconstruction, local identities and evidence; an optional isolated REAL_C1 recorded-video pipeline and independent human-review interface. Beta: authorized synchronized footage, evaluated detector/OCR, validated camera graph and calibrated policies. Production: external identity/MFA, retention policy, operational hardening, hardware/load evaluation and audited deployment. No live feed access, training, owner lookup, face recognition, public deployment or measured AI accuracy in this phase.

## Assumptions and risks

The handbook was not available in the initial empty repository. Six cameras use fictional schematic coordinates; no spatial query requires PostGIS geometry. PostgreSQL/PostGIS remains the database deployment. Passage IDs come from the source; repeated independent IDs cannot be magically deduplicated. OCR records declare a complete reading batch; additional readings use a new input revision, not mutation. Timing and confidence thresholds are provisional. Bounded graph queries may return truncated results explicitly. Historical run clocks are separate from wall clock. Camera coverage uses synthetic heartbeat freshness, not measured physical uptime.

Runtime dependencies: Python 3.12, PostgreSQL/PostGIS, Node, Docker Compose. Docker absence blocks Compose verification, not a license to substitute SQLite. Tests use real PostgreSQL. Recognition and linking correctness on synthetic fixtures establishes software behavior only.

## Executable traceability

| Requirements | Concrete checks |
|---|---|
| R01, R07 | `test_duplicate_concurrency_conflict_and_replay`, `test_lease_reclaim_idempotent_handler_poison_and_restart`, `test_receipt_evidence_metadata_and_transaction_rollback`, `scripts.e2e` |
| R02, R05 | `test_scenario_outcomes` (all 12 named fixtures), `test_database_immutability_and_heartbeat_interval_union` |
| R03 | `test_normalize`, `test_consensus_boundary_duplicate_and_unsupported` |
| R04 | `test_directed_impossible_collision_and_branch`, normal/impossible/ambiguous/collision scenario assertions |
| R06 | `test_watchlist_roles_validity_suppression_and_audit`, `test_invalid_windows_idempotent_commands_and_watch_expiry`, review-version test |
| R08 | `test_scope_provenance_and_evidence_failures`, viewer/evidence denial assertions, Chromium viewer test |
| R09 | `tests/e2e/console.spec.ts`, frontend type/build checks, OpenAPI consistency |
| R10 | `test_late_version_and_review_preserve_machine`, direct database immutability test, clean-migration/PostGIS test |

Original scenario acceptance is measured against compact synthetic inputs; the later recorded slice verifies actual inference, persistence and pixel provenance, not recognition accuracy. See `docs/validation_report.md` for the executed environment/results and `docs/review.md` for findings fixed during independent review.

## Recorded extension acceptance (audited 2026-09-05)

| ID | Requirement | Delivered gate / remaining boundary |
|---|---|---|
| R11 | Registered recorded video through actual detector/tracker/plate crop OCR | `scripts.recorded_acceptance` and `scripts.audit_recorded`: first 60 s, durable recovery/replay and exact source-pixel checks; real cross-camera accuracy remains untested |
| R12 | Independent recognition evaluation and source-timeline review | `test_evaluation_postgres`, unit evaluation denominators and Chromium source-video seek; labels separate from machine outputs; human completion is outstanding |

See [requirement-by-requirement audit](docs/progress_audit.md) for validation mode, acceptance gates and remaining work. The >90% Indian full-plate target requires a representative, independently labelled, locked evaluation; no synthetic confidence or acceptance total satisfies it.
