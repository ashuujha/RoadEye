# Phase 2 continuation audit — bounded vehicle Re-ID comparison

Budget allocation: hours 18–21, pulled forward from the earlier conditional
34–40 allocation; total remains 56 hands-on hours / four calendar days.
The user approved this bounded checkpoint before frontend work.

## Completed and verified

- **PASS:** Added the optional official FastReID VeRi SBS ResNet-50-IBN encoder,
  using existing torch/torchvision on CPU. Download: 198,261,759 bytes; SHA-256
  `57fb9c17d88911ea64390bf5427f43511435e7f88f6eed9dbc969d4b611e53cd`.
  The published configuration declares VeRi training. RoadEye trained on no
  CityFlow data. No additional dependency was installed.
- **PASS:** Strict checkpoint loading and raw-descriptor parity with pinned
  upstream backbone, IBN, non-local and pooling operations. Maximum absolute
  difference on the synthetic parity inputs: **0.0**. This verifies the adapter,
  not recognition accuracy. See `reid-encoder-parity.json` and the attributed
  upstream source/license in `third_party/fastreid/`.
- **PASS:** Optional causal quality prefix: first three eligible crops, spacing
  and maximum waiting time explicit. Future frames cannot alter past crop
  selections. Actual track start, first usable crop, and identity readiness are
  distinct timestamps. Exclusions retain reasons.
- **PASS:** Explicit development/evaluation roles, immutable selection manifest,
  source/config fingerprints, and recall over all mappable baseline tracks to
  prevent quality-filter exclusions from inflating the selection objective.
- **PASS:** Reused existing importer, association constraints, ambiguity rejection,
  independent RoadEye IDs, evidence/journey outputs and offline evaluator. Earlier
  S04 prediction hashes remain unchanged; 4,719 evidence crop hashes verified.
- **PASS:** Real vehicle-encoder CPU/offline check on three cached tracklets:
  maximum descriptor difference **2.9802322387695312e-08**. GT access, evaluator
  import, and network connections were blocked. Quality-run decisions at 50,
  100 and 150 seconds were identical to the corresponding full-run prefixes
  (128, 204 and 279 decisions); all 981 crop hashes and eight link evidence
  timestamps passed verification.

## Development results — S01 only

The fixed window is 0–180 scenario seconds across all five S01 cameras, selected
without identity annotations. It contains 1,154 predicted baseline tracklets.
There are 115 true cross-camera pairs among GT-mappable baseline tracklets under
the existing IoU/coverage/purity protocol.

| Variant | Embedded tracks | Crops | Causal retrieval rank-1 | Retrieval mAP | Correct/evaluable links at original thresholds | Unknown links |
|---|---:|---:|---:|---:|---:|---:|
| Original ImageNet prefix | 1,062 | 3,186 | 6/73 (8.22%) | 0.18493 | 2/5 | 58 |
| VeRi model, original prefix | 1,062 | 3,186 | 13/73 (17.81%) | 0.24839 | 1/1 | 6 |
| VeRi model, quality prefix | 327 | 981 | 11/40 (27.50%) | 0.35414 | 2/2 | 6 |

Retrieval uses a labelled gallery and each variant's available causal prefixes;
the quality variant has a different query/gallery population. Its percentage
must not be presented as a like-for-like end-to-end gain. One or two correct
scored links do not verify all the unknown links.

**FAIL — replacement selection:** none of the 30 predeclared configurations
combined at least ten evaluable links with at least 80% observed link precision.
For example, VeRi prefix at similarity 0.7 / margin 0.03 produced 5/6 correct
evaluable links, while similarity 0.6 / margin 0.03 produced 5/12. Neither qualifies.
The evidence threshold was not lowered after inspecting results.

The predeclared fallback retains ImageNet and the original 0.85 / 0.03 policy.
Selection was frozen at **2026-09-07 18:41:31 UTC** and committed as **`5cdfd51`**
before S05 inference or scoring. `reid-development.json` contains all grid metrics;
`reid-selection.json` records the rejected promotion and frozen fingerprints.

Offline S01 diagnostics found an admissible same-vehicle candidate for all 73
full-prefix scored queries and all 40 quality-prefix queries. The VeRi encoder
ranked a correct candidate first in only 13/73 and 16/40 respectively even after
pairwise gates removed invalid candidates. This optimistic labelled-gallery
diagnostic ignores unlabelled distractors and group constraints. It points to
appearance discrimination as the main development weakness.

## S05 input evidence

- **PASS:** Clock-selected 0–180-second window across all 19 cameras, frozen
  before reading identity annotations. No camera or vehicle was cherry-picked.
- **PASS:** Metadata-only inspection found two source rows with nonpositive box
  dimensions in c025. Row 3526 (frame 160, time 15.9 s) is inside the window;
  row 103751 (frame 4218, time 421.7 s) is outside. The explicit
  `exclude_nonpositive_and_record` policy records both and preserves originals.
  Other validation remains strict.
- **PASS:** After excluding the one invalid in-window row: **6,609 baseline
  tracklets, 570,113 valid observations**, 5,901 tracks with at least three
  observations before clipped-crop validation.
- **PASS — frozen inference:** 5,901 embedded/assigned tracklets produced 147
  links and 5,754 independent RoadEye global IDs. There are 5,616 one-camera,
  129 two-camera and nine three-camera predicted groups. Prediction hashes were
  frozen before evaluation. Crop extraction took 679.26 s; CPU embeddings took
  1,472.93 s; association took 71.05 s. These are full preparation/run times,
  not per-request latency.
- **PASS — integrity:** cached inference completed with GT/evaluator/network
  access blocked and produced identical prediction hashes. Decisions through
  50, 100 and 150 seconds matched the full run (1,804, 3,340 and 4,921 decisions).
  All 17,703 evidence crop hashes and all 147 link evidence cutoffs passed.
  Re-embedding three real tracklets on CPU matched exactly (maximum difference
  0.0). The 708 exclusions are all tracks with fewer than three observations.
- **MEASURED — label coverage:** 473 of 6,609 baseline tracklets passed the
  evaluator's one-to-one IoU, observation-coverage and identity-purity mapping;
  464 were ambiguous and 5,672 unmatched. The window contains 75,532 GT rows
  and 802 GT identity/camera visits; 442 visits were recovered (55.11%).
- **MEASURED — association:** 2/4 evaluable links were correct (**50.0% observed
  precision**); two were incorrect and 143 unscored. Evaluable coverage was
  4/147 (**2.72%**). Because labels are partial, all-link precision is bounded
  only between 1.36% and 98.64%; this is not a confidence interval. Pairwise
  global-ID precision was 2/4 (50.0%) and recall was 2/647 (**0.31%**).
- **MEASURED — retrieval:** causal labelled-gallery rank-1 was 16/297 (**5.39%**)
  and mAP was 0.06404. Offline pair-level analysis found at least one admissible
  positive for 281/297 queries, but ranked it first for only 31; only three had
  an admissible positive at or above the 0.85 runtime threshold. Sixteen queries
  lost all positives to pairwise gates; rejected positive-pair counts were 131
  stale and 21 physically implausible transitions. This diagnostic is optimistic
  and not an end-to-end accuracy result.
- **FAIL — crop-to-six-camera target:** the maximum predicted group spans three
  cameras, but the maximum fully scored consistent prediction spans **two**.
  S05 does support the task: raw GT includes 40 identities across at least six
  cameras, while baseline-to-GT mapping recovers ten identities across at least
  six cameras and one across nine. Current association did not reconstruct one.

The exact sanitized outputs are `reid-s05-metrics.json`,
`reid-s05-integrity.json`, and `reid-s05-error-analysis.json`.

## Tests and limitations

**PASS:** 31 tests passed; targeted Ruff checks and `pip check` passed. New tests
cover causal quality selection, incomplete prefixes, explicit data roles,
corrupt checkpoints, unknown models, invalid source rows, exclusion-aware recall,
and frozen-configuration tampering/line-ending portability. Existing leakage,
association, metric and provenance tests remain included.

**UNVERIFIED/deferred:** novel-site or novel-identity generalization; upstream
MTSC training provenance/causality; exact surveyed GPS and road connectivity;
score calibration; GPU fine-tuning/Colab export; OCR/ANPR; frontend and full demo.
S05 shares locations/cameras with the previously inspected S04 diagnostic.
These are local fixed-window results with partial annotations, not an official
CityFlow benchmark or a city-wide accuracy claim.

Development crop/embedding wall times were 144.80/413.60 s (ImageNet),
96.69/807.49 s (VeRi prefix), and 137.90/292.13 s (VeRi quality). Runs overlapped
on the same CPU; these are recorded processing times, not isolated latency tests.

## Deviations and next decision

The approved continuation spends a capped three-hour allocation before the
frontend phase, moving that phase to hours 21–27 while preserving the 56-hour
total. It adds one disclosed S05 import repair. During development scaffolding,
the ImageNet grid was recomputed from cached features with the corrected
all-mappable recall denominator before selection. No S05 tuning, no fabricated
links, no runtime GT identities, no training, and no frontend changes occurred.

## Failed and recommended next decision

- **FAIL:** the vehicle-specific pretrained replacement did not meet the S01
  evidence/precision gate, so it was not promoted.
- **FAIL:** frozen S05 association has extremely low pairwise recall (0.31%) and
  does not produce a verified six-camera journey. It is not ready for the core
  demo claim.
- **UNVERIFIED:** unscored predictions remain unknown. Do not count them as
  correct or use the three-camera predicted maximum as verified evidence.

The highest-impact next step is a separately approved, portable GPU fine-tuning
job on **training-only S01/S03 identity labels**, with vehicle-aware metric loss,
causal multi-frame aggregation and thresholds calibrated only within training
development folds. Keep runtime inference CPU-only. Because S05 has now been
consumed, any repeat there must be described as post-hoc comparison rather than
a fresh held-out result. S02 can provide a separate held-out check but cannot
validate a six-camera journey. The frontend phase can begin instead, but it would
visualize a maximum two-camera verified journey with the present artifacts.

Stop at this audit/local-commit checkpoint and wait for the user's decision.
