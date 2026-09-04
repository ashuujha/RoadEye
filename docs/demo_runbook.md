# Seven-minute judge demonstration

Rehearse locally before presenting. This is a software processing demonstration with synthetic passages and supplied mock OCR candidates. It does not establish recognition accuracy or real-world tracking.

## Preparation

```bash
make setup
make up
make demo
```

Sign in at http://localhost:5173 as administrator using the local password from ignored `.env`. Use UTC window **2026-01-15T08:00:00Z → 2026-01-15T09:00:00Z** and synthetic plate **ZZ01AA0001**. Rehearse separate actor login using the same local bootstrap password. Native startup alternative is in README; Docker was unavailable in the implementation environment.

For each scenario: Scenario runner → choose scenario → Create run → play → wait for `delivered` and all jobs `done`. `delivered` alone is not processing completion. Select the run in the top scope selector. New runs reset scenario scope without deleting anything. Pause stops delivery; received jobs still drain.

## Script

| Time | Action | Defensible result |
|---|---|---|
| 0:00–0:35 | Explain BEL SIH2026172 and visible synthetic banner. | “Passages/candidates are fictional; the database, processing and decisions are actual software.” |
| 0:35–1:15 | Create/play normal_journey; Overview. | 18 done jobs; 3 passages; 3 accepted; no review/rejections; historical clock 08:02. |
| 1:15–1:55 | Observation inspector → select C1; expand original input; open evidence. | Raw supplied candidate .95, normalized ZZ01AA0001, CONSENSUS_ACCEPTED, policy/thresholds; SVG says SYNTHETIC EVIDENCE. Clarify no OCR ran on it. |
| 1:55–2:35 | Trajectory explorer → reconstruct plate. | Observed C1/C2/C3; two inferred 60 s links, each 1000 m. Blue dashed links are inferred roads, green nodes are sightings. |
| 2:35–3:05 | Create/play impossible_travel; query. | C1→C6 in 5 s, IMPOSSIBLE_TRAVEL; no accepted inferred link. |
| 3:05–3:35 | Create/play ambiguous_branch; query. | C2→C3 and C2→C4 retained as ambiguous. No arbitrary chosen physical vehicle; definite flow excludes them. |
| 3:35–4:05 | Create/play unreadable_plate; Analytics. | 1 passage,0 accepted,1 rejected; vehicle counting remains independent of OCR. |
| 4:05–5:10 | Create/play watchlist_match. Alerts and review: create draft for plate, reason and current window. Sign out; sign in as approver; select run; approve. Sign out; sign in as investigator/admin. | Approval scans persisted accepted evidence. Exactly 1 active alert with supporting evidence. Classify true within synthetic scenario, enter notes, acknowledge; audit records actor/action. |
| 5:10–5:40 | Return to normal run; note 3 passages; Scenario runner → replay. | 18 unique done jobs/version 18 and 3 passages remain; delivery is at least once with idempotent effects. |
| 5:40–6:20 | Create/play camera_outage; Overview. | C6 is stale at 180 s; other five fresh. Missing coverage is explicitly distinct from low traffic. |
| 6:20–7:00 | Explain next adapter connection and limitations. | Authorized real frames → detector → within-camera tracking → OCR candidates → this existing durable pipeline. Future validation must measure full-plate errors, counts and link accuracy on held-out connected footage. |

Optional congestion drill: create/play congestion_proxy; Analytics shows 4 C1→C2 samples, median 120 s, p90=180 s, declared synthetic baseline 60 s, ratio 2. These are a traffic proxy and segment-average speeds, not density or instantaneous speed.

Optional late-input drill: create late_arrival paused; click step 10 times and wait for 10 done jobs. Query: C1 and C3 observed, C2 only inferred along the road path. Play remaining events; query again: C2 is now observed, version increases. The old query stays immutable and reports stale.

## Worker recovery drill

```bash
docker compose stop worker
```

Create worker_recovery paused. Step 7 times. Status must show 7 pending jobs and 0 counted passages; a successful receipt does not mean processed. Then:

```bash
docker compose start worker
```

Play, wait for 18 done jobs, verify 3 passages. Replay still produces 3. The automated native alternative `uv run python -m scripts.e2e` starts/stops its own worker and checks this behavior; run with API up and no other worker.

## Backup replay method

If browser interaction fails but API/worker are healthy:

```bash
uv run python -m scripts.demo --scenario normal_journey
uv run python -m scripts.demo --scenario impossible_travel
uv run python -m scripts.demo --scenario ambiguous_branch
uv run python -m scripts.demo --scenario unreadable_plate
uv run python -m scripts.demo --scenario camera_outage
```

These invoke actual API writes and print backend-derived summaries. They do not play back stored screenshots or ground-truth outputs. Inspect `/docs` and the selected run's durable status to diagnose failures. Never claim a pending/poison job completed.

## Likely questions

- “What AI accuracy did you achieve?” None measured here. Candidate scores are supplied heuristic inputs. Synthetic tests prove software behavior only.
- “Is that the vehicle's actual route?” Camera nodes are observed synthetic sightings; road links are constrained inferences. Same plate text can collide and multiple alternatives remain.
- “Does unreadable mean no vehicle?” No: passages are independent of OCR, as the unreadable scenario demonstrates.
- “What happens on restart?” Received input and jobs are durable; leases recover, and uniqueness/transactions suppress repeated effects. Delivery is not exactly once.
- “Why no Kafka?” A PostgreSQL outbox covers this bounded single-team MVP with fewer operational dependencies.
- “Can this operate city-wide now?” Not yet: real model integration, authorized synchronized data, identity/security hardening and target-hardware capacity measurements remain.
