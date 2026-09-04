# API contracts

FastAPI exposes `/v1`; `/openapi.json` and `/docs` derive from implemented Pydantic schemas. `packages/roadeye/openapi.json` is the committed snapshot; `apps/web/src/api.generated.ts` comes from openapi-typescript and is used by openapi-fetch. Core run, observation, journey, alert and analytics responses are explicitly typed. Inspection metadata uses extensible JSON objects.

Errors have `error` and `correlation_id`; validation errors list field locations without echoing sensitive inputs. Every response disables caching. Writes require `X-RoadEye: console`, local same-origin policy, authentication and role checks. Use UUID-valued `Idempotency-Key` headers on ingestion, run/control, configuration, watchlist, review and acknowledgement writes. Keys are scoped by actor/operation (and run for inputs); matching payload retries return the saved response, differing payloads return 409. Trajectory queries store independent read snapshots and do not require a key.

| Area | Routes | Authorization |
|---|---|---|
| Health | GET `/health/live`, `/health/ready` | Public local health |
| Local sessions | POST `/auth/login`, `/auth/logout`; GET `/auth/me` | Demo enabled; password; expiring session cookie |
| Network | GET `/cameras`, `/cameras/{id}`, `/graph`; PUT `/cameras/{id}`, `/graph` | Read: authenticated; configure: administrator |
| Inputs | POST `/inputs` | Administrator; 202 means durably received |
| Observations | GET `/observations`, `/observations/{id}` | Investigator or administrator |
| Evidence | GET `/evidence/{id}` | Investigator or administrator; digest checked |
| Journeys | POST `/trajectories`; GET `/trajectories/{id}` | Investigator or administrator |
| Analytics | GET `/analytics/{summary,counts,od,travel_times}` | Authenticated; includes metric metadata |
| Watchlists | GET/POST `/watchlists`; POST `/watchlists/{id}/{approve,revoke}` | Create: investigator/admin; approve/revoke: separate approver |
| Alerts | GET `/alerts`; POST `/alerts/{id}/acknowledge` | Investigator/admin |
| Reviews | POST `/observations/{id}/reviews` | Investigator/admin |
| Audit/jobs | GET `/audit`, `/jobs` | Investigator/admin for audit; admin for jobs |
| Replay | GET `/demo/scenarios`, `/demo/runs`, `/demo/runs/{id}`; POST `/demo/runs`, `/demo/runs/{id}/control` | Demo enabled; writes: administrator |

All paths in the table have `/v1` prefix. Search and analytics take `run_id`, UTC `start`/`end` (half-open, positive, at most 24 h). Observation search supports exact normalized `plate`, `offset` ≤1000 and `limit` ≤200. Queries reject overly dense windows. Trajectories accept `plate`, `include_review`, `limit` ≤200; similarity is at most one character, weak links remain review candidates. Runs cap at 500 distinct inputs. Graph depth is four hops with at most 32 paths per pair.

Input kinds are `passage`, `ocr`, `heartbeat`. Passage and OCR events share camera-local `passage_id`, capture timestamp and evidence reference. OCR is a complete immutable batch with frame IDs and candidate-specific scores. Each input includes schema version 1, event UUID, run UUID, camera/lane, capture time, quality/input scores, evidence key, synthetic provenance and mock inference origin. Missing passage work retries; malformed or unavailable evidence returns a real error. Supplied inputs cannot switch to real mode.

Play schedules one fixed event per worker tick. Pause stops further delivery, not already received processing. Step durably emits one event. Replay resets delivery cursor only. Retry resets poison jobs for the selected run after the underlying issue is resolved. Run `delivered` means all inputs were emitted; inspect job states for processing completion. Poll durable status; no ephemeral notification stream is required.
