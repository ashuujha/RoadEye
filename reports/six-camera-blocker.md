# Six-camera journey blocker

## Current result - FAIL

CityFlow has real long multi-camera identities: feasibility found identity 260
across 24 S04 cameras. RoadEye has not predicted a fully scored, identity-consistent
six-camera group. The frozen S02 demo reaches three predicted cameras and two
fully verified cameras. The disclosed S05 post-hoc diagnostic reaches five
predicted cameras and two fully verified cameras.

## Evaluation inventory

| Scenario | Released identity labels | RoadEye use | Remaining role |
|---|---:|---|---|
| S01 | Yes | Re-ID training/development and association selection | Development only |
| S03 | Yes | Re-ID training/development | Development only |
| S04 | Yes | Feasibility-selected and consumed diagnostic | Post-hoc only |
| S02 | Yes | Consumed frozen trained-model evaluation | Post-hoc only |
| S05 | Yes | Consumed evaluation, then disclosed post-hoc repair | Post-hoc only |
| S06 | No locally released GT | Untouched test video | Cannot verify a six-camera identity locally |

There is no unused locally labeled CityFlow scenario left for a fresh held-out
six-camera claim. S06 has six cameras but no released GT, so it cannot turn a
prediction into a verified result. Reusing S04/S05 after tuning must be called
post-hoc diagnostic evidence.

## Recommended repair

Use S01 and S03 development identities to improve camera-domain robustness and
association calibration, with no labels in runtime. Then run one explicitly
post-hoc S04/S05 diagnostic and accept the result whether or not it reaches six.
This may produce a real six-camera demo journey, but it cannot restore fresh
held-out status. A fresh accuracy claim requires another approved labeled
multi-camera dataset or access to an official S06 evaluator.

Until one of those paths succeeds, the demo must retain the honest two-camera
verified maximum and may show the three-camera S02 prediction with unknown
members clearly labeled.
