# RoadEye requirements — SIH2026172

Bharat Electronics Limited problem: inspect city-wide ANPR sightings, plausible camera journeys and traffic patterns. Users are investigators, traffic analysts, administrators and separate watchlist approvers. This repository implements a local synthetic engineering demonstration; recognition accuracy is not measured.

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

MVP: one fictional network, supplied mock OCR candidates, bounded query reconstruction, local identities and evidence. Beta: authorized synchronized footage, evaluated detector/OCR, validated camera graph and calibrated policies. Production: external identity/MFA, retention policy, operational hardening, hardware/load evaluation and audited deployment. No real feed access, training, owner lookup, face recognition, public deployment or measured AI accuracy in this phase.

## Assumptions and risks

The handbook was not available in the initial empty repository. Six cameras use fictional schematic coordinates; no spatial query requires PostGIS geometry. PostgreSQL/PostGIS remains the database deployment. Passage IDs come from the source; repeated independent IDs cannot be magically deduplicated. OCR records declare a complete reading batch; additional readings use a new input revision, not mutation. Timing and confidence thresholds are provisional. Bounded graph queries may return truncated results explicitly. Historical run clocks are separate from wall clock. Camera coverage uses synthetic heartbeat freshness, not measured physical uptime.

Runtime dependencies: Python 3.12, PostgreSQL/PostGIS, Node, Docker Compose. Docker absence blocks Compose verification, not a license to substitute SQLite. Tests use real PostgreSQL. Recognition and linking correctness on synthetic fixtures establishes software behavior only.
