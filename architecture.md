# RoadEye architecture — SIH2026172

A modular monolith exposes FastAPI and a separate worker sharing `packages/roadeye`. PostgreSQL is the sole state authority. The browser polls durable state. Evidence bytes live outside relational rows. Domain modules separate contracts, plates, trajectories, analytics, jobs and application services without a repository class for every table.

```mermaid
flowchart LR
  Console[React console] --> API[FastAPI /v1]
  API --> PG[(PostgreSQL + PostGIS)]
  Worker[Worker process] --> PG
  API --> Evidence[Local evidence store]
  Fixtures[Synthetic inputs] --> API
```

```mermaid
sequenceDiagram
  participant S as Source
  participant A as API
  participant D as PostgreSQL
  participant W as Worker
  S->>A: Versioned input + idempotency key
  A->>D: Transaction: input + outbox + audit
  A-->>S: Durably received
  W->>D: Lease eligible job, SKIP LOCKED
  W->>D: Transaction: passage/OCR/observation/alerts + done
  A->>D: Query event-time observations and derived metrics
```

Inputs belong to immutable runs/dataset manifests. Runs belong to a fictional network. Cameras belong to zones; lanes belong to cameras; directed edges connect cameras. Inputs reference runs; passages reference input/run/camera/lane; readings and candidates preserve contributions; observations preserve machine decisions; review revisions overlay those decisions. Evidence metadata references immutable objects. Query snapshots carry run versions. Watchlists and approvals are scoped; alerts link supporting observations and evidence. Actions and sensitive reads create audit rows. Sessions store token digests.

Jobs have unique event IDs, available time, attempts, lease token/deadline, error and pending/leased/done/poison states. Expired leases are reclaimable. Domain effects and job completion commit together. Backoff is bounded; exhausted jobs remain inspectable. Delivery is at least once. Input idempotency compares canonical payload digests; business uniqueness constraints prevent duplicate effects. Run-row locking serializes derived version increments and processing within each run.

Graph reconstruction hard-rejects disconnected, reversed and implausibly fast/slow links before scoring. Multiple plausible links and road paths remain visible. Camera sightings are observed; roads between them are inferred. No physical identity is guaranteed by identical text. Traffic counts use passages independently of plate acceptance. Aggregates use half-open UTC capture windows. Late data increments the run version; query snapshots remain immutable and new queries recompute.

Evidence storage validates relative object keys and digests; protected retrieval returns honest missing-object errors. Backup includes database and object directory at a consistent checkpoint. S3 migration replaces the store interface using the same digest/object metadata, with private objects and authenticated delivery. Orphan cleanup must compare keys to metadata after a grace period; it is never an indiscriminate directory deletion.

Local authentication is explicitly enabled by configuration, uses server-side expiring sessions and role checks, and must be replaced by production identity. Local login secrets are environment configuration, never browser constants. Cookie writes require a same-origin/custom-header boundary. Synthetic runs do not become live on replay. Real modes fail at startup until adapters exist. Model confidence is a heuristic input, not calibrated accuracy. PostGIS is installed for the future, but fictional schematic coordinates are not geographic coordinates.

## Implemented refinements

Durable receipt now records evidence digest/size/type/key in the same transaction as input and outbox insertion. Keys cannot silently change content within a run. Database triggers protect input/machine rows, audit history and run graph/provenance from updates. Core API payloads have typed response schemas; extensible inspection metadata remains JSON. Readiness requires the current migration head and a working PostGIS function.

```mermaid
stateDiagram-v2
  [*] --> pending: atomic receipt
  pending --> leased: claim + token + deadline
  leased --> done: effects + completion commit
  leased --> pending: failure / retry backoff
  leased --> leased: expired lease reclaimed with new token
  leased --> poison: attempts exhausted
  poison --> pending: administrator retry after repair
```

```mermaid
erDiagram
  RUN ||--o{ INPUT_EVENT : scopes
  INPUT_EVENT ||--|| JOB : schedules
  RUN ||--o{ EVIDENCE_ASSET : owns
  INPUT_EVENT ||--o| VEHICLE_PASSAGE : counts
  VEHICLE_PASSAGE ||--o| OBSERVATION : recognizes
  OBSERVATION ||--o{ REVISION : preserves
  OBSERVATION ||--o{ ALERT : supports
  RUN ||--o{ TRAJECTORY_QUERY : versions
```

Heartbeat freshness uses the run clock; window coverage unions the 120-second validity intervals from processed heartbeat inputs. This is a declared coverage proxy, not physical uptime. Query execution locks the run during snapshot construction to keep versions/results consistent with processing and review transactions.

Container builds use a pinned uv binary with `uv sync --frozen --no-dev`, following the [official uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/) and [lock/sync behavior](https://docs.astral.sh/uv/concepts/projects/sync/). The uv pin matches the locally exercised 0.12.1 lockfile tooling. Docker execution remains a separate unverified runtime check in this environment.
