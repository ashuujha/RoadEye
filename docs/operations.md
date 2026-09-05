# Local operations

`make setup` preserves existing .env and installs lockfiles. `make up` binds all exposed services to loopback and waits for PostgreSQL health/migrations. API readiness queries the migration table and PostGIS library. Liveness proves only the API process. The worker is a separate process and uses durable job state; pending/leased/poison counts and oldest pending receipt expose lag. A reachable API does not prove that its worker is running.

## Worker recovery

Jobs are claimed with SKIP LOCKED and committed leases (30 s default). A handler takes run/job locks, verifies its lease token, and commits business writes together with done state. Crash before effect commit rolls back; expired leases can be reclaimed. Stale tokens cannot complete work. Exceptions roll back effects, retain an error type/message, and schedule 2^attempt seconds backoff (max 60 s). Three failures produce poison. The administrator's retry control resets only poison jobs in the selected run. Fix the input/dependency problem first; retrying does not fabricate success. Delivery is at least once, not exactly once.

Pause stops source delivery only. To demonstrate processing failure, stop the worker, step inputs through the API, observe pending work, and restart the worker. The process E2E script performs this without editing database state. API/worker restarts must not erase inputs. Shutdown allows the current transaction to finish; a forced crash relies on leases.

## Verification and configuration

For integration/process tests, use a disposable test database and stop other workers. `make validate` requires API and frontend running; its process/browser scripts each manage their own worker. With Compose: `docker compose stop worker`, `make validate`, `docker compose start worker`. Browser prerequisites: `cd apps/web && npx playwright install chromium` (Linux may require OS browser dependencies). Tests require CREATEDB permission for the clean-database migration check. Production runtime roles should not have that privilege.

Configuration prefix is ROADEYE_. Database URL must be postgresql+psycopg. Demo mode defaults off; enabling it requires a 16+ character local password. Source mode other than synthetic fails explicitly. Provisional consensus accept score=.8, margin=.2; lease=30 s, max attempts=3. Evidence root defaults to versioned synthetic evidence. CORS is explicitly http://localhost:5173. Graph edits apply only to newly created run snapshots. Runs accept at most 500 unique events, queries at most 200 candidates, graph expansion at most 4 hops/32 paths. Narrow windows or create another synthetic run when limits are reached.

UTCClock supplies wall time and is injectable in tests; run clocks advance from fixed capture times. Scheduling replays manifest order and never rewrites capture times. Processing lag uses receipt/wall time. Historical synthetic data is never labelled live.

## Evidence and backups

Initial store serves small read-only local objects. It rejects traversal, validates digest and size on retrieval, and returns 404 for missing objects or 409 for integrity mismatch. Missing evidence never returns a fabricated image. Bytes remain outside relational rows. Database and evidence must be backed up together.

Example for the named Compose project:

```bash
mkdir -p .runtime/backup
docker compose stop worker
docker compose exec -T db pg_dump -U roadeye -Fc roadeye > .runtime/backup/roadeye.dump
cp -a data/synthetic/evidence .runtime/backup/synthetic-evidence
# For recorded-capable native installations, also preserve the configured
# ROADEYE_RECORDED_EVIDENCE_ROOT, source recording, registry and model manifest.
# Default recorded evidence directory (if present):
cp -a .runtime/evidence .runtime/backup/recorded-evidence
docker compose start worker
```

For a consistent backup, also pause writes/source controls while taking both snapshots. Restore into a new empty database with `pg_restore -U roadeye -d <new_database>`, restore the matching object directory, point a stopped stack at it, run migrations/readiness, and reconcile counts/digests before use. Do not overwrite unrelated databases. These backup commands are documented procedures, not a claimed backup/restore drill.

Recorded writable evidence now uses content-addressed keys and atomic temporary-file rename before domain reference. The immutable original MP4 and its registry digest must be preserved separately from extracted evidence. Independent labels live in PostgreSQL and belong in the protected database backup. A periodic orphan report can compare object keys to evidence_assets; delete only unreferenced objects older than a documented grace period after operator review. No automatic cleanup is implemented. An S3-compatible store can implement EvidenceStore.read with private bucket access, identical metadata/digest checks and authorization through API; neither MinIO nor paid services are required now.

No public deployment, remote push, enforcement action, external camera feed or dataset download belongs to these operations.

## Observed source-video shutdown limitation

During the 2026-09-05 audit, a retired API process remained waiting for old source-video connections after graceful shutdown. The updated API was already healthy; the retired process required forced termination. PostgreSQL and worker processing were preserved. Configure and exercise a finite Uvicorn graceful-shutdown timeout and client cancellation before operational deployment. The audit's successful worker recovery is not a claim that all HTTP streaming shutdown paths are hardened.
