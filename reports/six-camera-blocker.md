# Six-camera journey blocker

## Current result - FAIL

CityFlow has real long multi-camera identities: feasibility found identity 260
across 24 S04 cameras. RoadEye has not predicted a fully scored, identity-consistent
six-camera group. The frozen S02 demo reaches three predicted cameras and two
fully verified cameras. The final frozen S01/S03-calibrated post-hoc diagnostic
reaches 16 predicted cameras on S04 and eight on S05, but both scenarios still
reach only two fully scored identity-consistent cameras. Large raw groups contain
mixed or unscored members and cannot be presented as verified journeys.

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

The approved S01/S03 repair has now been exhausted. It froze pure trained Re-ID,
a 0.675 cosine threshold, zero margin, and a 45-second maximum gap after measuring
7/8 correct evaluable development links. Its single S04/S05 post-hoc run failed.
Do not tune again on S02/S04/S05. The highest-impact next experiment requires a
fresh development source with camera diversity closer to S04/S05, followed by a
new approved labeled holdout or the official S06 evaluator.

Until one of those paths succeeds, the demo must retain the honest two-camera
verified maximum and may show the three-camera S02 prediction with unknown
members clearly labeled.
