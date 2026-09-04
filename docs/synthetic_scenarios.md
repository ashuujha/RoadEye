# Exact scenario outcomes

Default query window: 2026-01-15T08:00:00Z to 09:00:00Z. Query plate ZZ01AA0001 except congestion's four distinct ZZ01BB identifiers. Each scenario has initial/final heartbeats; duplicates preserve event IDs. Vehicle totals count camera passages, not unique physical vehicles.

| Scenario | Passages | Accepted | Review | Rejected | Additional expected outcome |
|---|---:|---:|---:|---:|---|
| normal_journey | 3 | 3 | 0 | 0 | C1→C2→C3; two 60 s/1000 m inferred links; one enrolled C1→C3 session |
| ocr_disagreement | 1 | 0 | 1 | 0 | Two unique frames despite repeated f1; alternatives 0001/0002 each score .45; LOW_SCORE |
| unreadable_plate | 1 | 0 | 0 | 1 | NO_SUPPORTED_CANDIDATE; recognition coverage 0 |
| impossible_travel | 2 | 2 | 0 | 0 | C1→C6 in 5 s rejected IMPOSSIBLE_TRAVEL; one rule indicator |
| ambiguous_branch | 3 | 3 | 0 | 0 | C2→C3 at 60 s and C2→C4 at 65 s both ambiguous; no definite flow/OD; C3→C4 has NO_DIRECTED_PATH |
| watchlist_match | 1 | 1 | 0 | 0 | Exactly one active watchlist alert after a separate actor approves a valid scoped matching entry; zero before approval |
| duplicate_delivery | 3 | 3 | 0 | 0 | Repeated six passage/OCR inputs create no extra business effects; replay leaves totals/version unchanged |
| late_arrival | 3 | 3 | 0 | 0 | Before C2 arrives: C1→C3 inferred through C2 without an observed C2 node; afterward: three observed nodes/two links and newer version |
| camera_outage | 1 | 1 | 0 | 0 | At run clock 08:03 C6 heartbeat is 180 s old, stale; other five fresh; one CAMERA_STALE indicator |
| congestion_proxy | 8 | 8 | 0 | 0 | Four C1→C2 links with [60,60,180,180]s; median 120, p90=180, baseline 60, ratio 2; median segment-average speed 40 km/h |
| plate_collision | 2 | 2 | 0 | 0 | Simultaneous C1/C6; SAME_PLATE_COLLISION rejected link; separate sighting hypotheses retained |
| worker_recovery | 3 | 3 | 0 | 0 | First seven stepped inputs without worker remain pending and passages=0; restart worker yields 3; replay still 3 |

Normal run: 18 unique jobs (12 heartbeat, 3 passage, 3 OCR), final version 18. Duplicate scenario has 24 delivery positions but only 18 jobs/version 18. Late scenario: six initial heartbeats + C1/C3 input pairs occupy the first 10 positions; step 10 times before querying, then play for observed C2. The run clock never rewinds when earlier events arrive.

The watchlist and recovery scenarios require the actor/process actions in the runbook; selecting input fixtures alone does not bypass approval or simulate a crashed worker. Classification true/false/uncertain refers only to the synthetic scenario.
