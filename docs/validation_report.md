# Measured validation report

Executed locally on 2026-09-05. This report measures software behavior on synthetic inputs, not AI recognition accuracy.

## Environment

- Python 3.12.13; uv 0.12.1; Node 24.18.0; locked application dependencies.
- Native isolated PostgreSQL 18.6 and PostGIS 3.6.2 on 127.0.0.1:55432. SQLAlchemy connections explicitly select UTC; new test databases explicitly use UTF8/template0.
- Actual FastAPI process on 127.0.0.1:8000, separate worker processes, Vite console on localhost:5173.
- Playwright 1.62.1 with actual headless Chromium 151.0.7922.34.
- No SQLite, repository-memory persistence, mock HTTP result server, external camera feed or paid service was used.

## Executed checks

| Check | Observed result |
|---|---|
| `make validate` with local database/browser environment | Passed full target |
| `make demo` | Passed through actual HTTP API; run b3767c23-029a-4024-a19f-2346290f6d81: 3 passages, 3 accepted, 18 done jobs, two 60-second links |
| Ruff lint and formatting | Passed; 31 Python files formatted |
| mypy | Passed; 17 application modules |
| Pytest unit + real PostgreSQL integration | 33 passed (12 unit,21 integration), one upstream Starlette/AnyIO deprecation warning |
| Independent clean database | Alembic migrations applied to new UTF8 database; expected head; real PostGIS ST_Distance=5 |
| All 12 named fixture scenarios | Exact passage/accepted/review/rejected totals checked; graph/coverage/congestion assertions where applicable |
| Concurrent duplicate ingestion | 12 concurrent requests; one new receipt; one passage effect; conflicting payload 409 |
| Durable rollback | Input/job/evidence metadata absent after rollback; present together after accepted receipt |
| Worker leases/retry | Expired lease reclaimed; stale token rejected; duplicate handler fenced; missing passage poisons after 3 attempts and recovers after repair/retry |
| Late arrival/review | New run result version; earlier query remains immutable/stale; raw machine decision retained after correction |
| Authorization/evidence/watchlists | Viewer searches/evidence denied; different approver required; validity end exclusive; unique alert suppression; acknowledgement audited; missing evidence 404 |
| Full PostgreSQL restart | Prior recovery run 73f13471-f91e-4850-bbce-c3c9b310e716 retained 3 passages and 18 done jobs after pg_ctl restart |
| Frontend Vitest | 1 test passed (missing data distinct from observed zero) |
| Frontend TypeScript + production build | Passed; 76 modules transformed; about 249 KB uncompressed JS /78 KB gzip |
| Generated API consistency | OpenAPI export and TypeScript regeneration produced no diff |
| Separate-process HTTP E2E | Passed durable receipt with worker absent, restart/replay, normal journey, evidence, unreadable counts, impossible/ambiguous links, watchlist approval/acknowledgement |
| Actual Chromium checks | 2 passed: console creates/processes run and inspects observations/journey/evidence/analytics; viewer empty/permission-denied states |
| Browser rendering | Screenshot inspected; no browser page errors in main journey test |
| npm dependency audit | Reported 0 vulnerabilities after patched tooling pins |
| Locked backend sync | `uv sync --locked --offline` succeeded |

Full target command used in this environment:

```bash
UV_CACHE_DIR=/tmp/roadeye-uv \
UV_PYTHON_INSTALL_DIR=/tmp/roadeye-python \
PLAYWRIGHT_BROWSERS_PATH=/tmp/roadeye-browsers \
ROADEYE_DATABASE_URL=postgresql+psycopg://roadeye@127.0.0.1:55432/roadeye \
make validate
```

API and frontend were running; no competing worker was running during integration/process tests. The process/browser scripts each started their own worker. The custom /tmp paths are specific to this task environment, not required project defaults. The test PostgreSQL instance is local and disposable.

## Failures found and corrected

Initial test collection lacked root package discovery; configured pytest pythonpath. A normalization test incorrectly rejected a supported positional 0→O alternative; corrected the expectation. Generated client checking caught required header/default-field omissions; corrected client calls. npm identified vulnerable initial tooling pins; upgraded patched versions and rechecked. Bare package extraction lacked PostGIS's control symlink; repaired the isolated runtime installation. Native PostgreSQL default SQL_ASCII and Asia/Kolkata timezone required explicit UTF8 test databases and UTC application sessions. Full validation caught a formatting mismatch; corrected it. Review also fixed atomic evidence metadata receipt, raw/provenance immutability, query errors, seed serialization and startup error secret redaction.

## Blocked or not executed

- `docker compose version` failed with `/bin/bash: docker: command not found` (exit 127). `sudo -n true` reported interactive authentication required. Compose image builds/startup and container-specific behavior are **not verified**; native execution is not claimed equivalent.
- Future Compose/CI target PostgreSQL 17/PostGIS 3.5 and Node 22.15. Native checks used PostgreSQL 18/PostGIS 3.6 and Node 24; the container matrix remains to be executed.
- GitHub Actions was not run. The workflow exists for future local-to-remote handoff; nothing was pushed.
- At the original synthetic milestone, backup/restore, target-hardware capacity, real detector/OCR integration, camera feeds and recognition/tracking evaluation had not been executed. The follow-up below now verifies recorded detector/OCR integration; the other operational/evaluation checks remain outstanding.
- Browser tests cover the essential normal journey and permission boundary; they do not claim every possible UI transition or accessibility certification.

## Interpretation

The native connected system and deterministic core behavior are verified. Synthetic candidate confidence, scenario success and passing tests do not establish real recognition accuracy or physical vehicle identity. Read `limitations.md` and `real_data_integration.md` before moving beyond this local phase.

## Recorded-video follow-up (native environment)

The subsequent recorded-video extension ran actual CPU vehicle detection, plate-specific detection and crop OCR on the provided Delhi clip. It produced 25 counted passages in [0,60), with 2 accepted, 6 review-required and 17 rejected machine observations; recognition accuracy is unmeasured. The original synthetic-only conclusions above describe the earlier milestone. See [recorded-video results](recorded_video_demo.md) for source/model hashes, measured runtimes, crop inspection, full recovery/replay verification and current limitations. Neither whole-clip inference, hosted CI nor Docker execution is claimed.

Current follow-up gates: `make validate` passed with writable temporary uv cache and native PostgreSQL configuration: 39 Pytest tests, 1 Vitest test, Ruff formatting/lint, mypy, TypeScript, generated-client consistency, production web build, synthetic process E2E and all 4 Chromium checks. The recorded acceptance script separately passed forced process interruption, recovery, duplicate replay and 99 authorized evidence retrievals; 39 retained PNG crops were also checked pixel-for-pixel against source PTS, with 25 anchor mappings checked.
