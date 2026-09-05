# RoadEye

**City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics**

SIH2026172 · Bharat Electronics Limited

A backend-first engineering MVP: real PostgreSQL persistence, durable processing, conservative plate consensus, constrained camera journeys, traffic analytics, evidence-linked alerts, review and audit. The React console shows actual API results.

**Synthetic scenarios remain supplied mock inputs. The optional Recorded video view now runs actual local vehicle detection, plate detection and OCR on the provided Delhi recording. Recognition accuracy remains unmeasured.**

## Start locally

Prerequisites: Docker with Compose v2, Python 3.12 through [uv](https://docs.astral.sh/uv/), Node 22.15+ and npm. Nothing is published or deployed.

```bash
make setup
make up
make demo
```

`setup` creates a unique ignored `.env` without overwriting existing configuration, installs locked backend/frontend dependencies, and leaves secrets out of bundles. `up` starts PostgreSQL/PostGIS, applies migrations, then starts API, worker and console. Read the local `ROADEYE_DEMO_PASSWORD` from `.env` to sign in as administrator at **http://localhost:5173**. API docs: **http://localhost:8000/docs**. Use localhost consistently for the configured CORS origin.

`make demo` creates and processes a normal journey through HTTP. Select its run in the console. Expected: three passages, three accepted observations, C1 → C2 → C3, two 60-second links. The full [seven-minute judge runbook](docs/demo_runbook.md) includes evidence, ambiguity, rejection, watchlists and recovery.

```bash
make down  # stops only this Compose project; preserves database volume
```

No Docker volume reset command is provided. To reset a scenario, create a new scoped run; replay redelivers original IDs into the existing run and preserves counts/history.

## Native development / verified fallback

With a real PostgreSQL/PostGIS database available, set `ROADEYE_DATABASE_URL` in `.env`, then:

```bash
make setup
make migrate
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
# Separate terminal:
uv run python -m apps.worker.main
# Separate terminal:
cd apps/web && npm run dev -- --host 127.0.0.1
```

The task environment lacked Docker and sudo privileges. The API, worker and console were executed natively against an isolated PostgreSQL 18.6 / PostGIS 3.6.2 instance. **Compose startup itself remains unverified here.** See [validation report](docs/validation_report.md) for exact checks and limitations; a workflow file is not evidence that hosted CI passed.

## Verify

Use an isolated database; integration tests create uniquely scoped synthetic runs and intentionally exercise failing jobs. Stop background workers during integration/process recovery tests.

```bash
make lint
make typecheck
make test
make client-check
cd apps/web && npm run build && npx playwright install chromium
# With API running and no other worker:
uv run python -m scripts.e2e
# With API/frontend still running, browser check starts its own worker:
make browser
```

`make validate` runs those checks in sequence; it requires API/frontend running and manages its own process E2E worker. The browser step also starts and stops its own worker. For a running Compose stack: `docker compose stop worker`, run validation, then `docker compose start worker`. `make generate` regenerates the API contract and TypeScript client; commit both generated files when changing schemas.

## Repository map

- `packages/roadeye`: contracts, relational models, ingestion/services, consensus, graph reconstruction, analytics, jobs, authentication, evidence.
- `apps/api`, `apps/worker`, `apps/web`: runtime entrypoints and connected console.
- `migrations`: explicit Alembic schema and immutability protections.
- `data/synthetic`: compact input fixtures and manifest; tests alone consume `ground_truth`.
- `tests`: domain, PostgreSQL integration and actual-browser checks.
- `scripts`: setup, replay driver, process E2E, fixture and contract generation.

Start with [PRD](PRD.md), [architecture](architecture.md), [API guide](docs/api.md), [operations](docs/operations.md), and [real-data handoff](docs/real_data_integration.md). See [limitations](docs/limitations.md) before interpreting outputs. No license grant has been inferred or added.

## Recorded Delhi video — native judge slice

The existing synthetic judge runbook is unchanged. For the recorded slice, use [the exact native startup, processing and review instructions](docs/recorded_video_demo.md). Keep `delhi_anpr.mp4` local at `data/recorded_real/delhi_anpr.mp4`; it and downloaded weights/evidence are excluded from Git.

```bash
make recorded-setup
# Set ROADEYE_RECORDED_ENABLED=true in your local API and worker environments.
# With the native services running:
make recorded-demo
```

In the console, sign in as administrator → **Recorded video** → **Process first 60 seconds** → select/inspect a passage. View original frames, lossless plate crops, raw OCR, consensus reasons and separate vehicle/accepted-plate counts. This is one recorded camera with assigned replay time, no geographic calibration, and no inferred routes/speed/congestion. A high model score is not measured accuracy.

## Fresh audit and independent review

The [progress audit](docs/progress_audit.md) distinguishes working backend features from real-world validation. Read the [recognition investigation](docs/recognition_error_analysis.md), [dataset decision](docs/dataset_decision.md) and [prioritized next steps](docs/next_steps.md). No evidence currently supports a 90% recognition claim.

The Recorded video view now includes an authenticated source-video timeline, vehicle/plate overlays, blank independent transcription/readability forms, missed-vehicle markers and durable review revisions. Start with the [numbered human-review instructions](docs/recorded_video_demo.md#independent-human-review-after-this-audit). Labels do not alter inference. The original run remains unchanged; a separate versioned cadence rerun has 25 predicted passages, 2 accepted, 8 review-required and 15 rejected, with accuracy still unmeasured. Keep the Indian recording; RoundaboutHD acquisition is deferred until the isolated experiment is ready.
