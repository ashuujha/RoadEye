# S01/S03 six-camera repair audit, hours 47-52

## PASS

- **Development isolation:** the private bundle contains 23 identity-disjoint
  development identities: 19 from S01 and four from S03. S02, S04, and S05 are
  absent. All other baseline tracklets remained runtime distractors. Released
  identities were used only by the development scorer, never by association.
- **S03 completion:** a metadata-only full declared interval from 0.000 to
  249.367 seconds was frozen across all six S03 cameras. CPU processing found 820
  baseline tracklets and embedded 322 from 966 hash-bound causal prefix crops.
- **Development calibration:** the first 528-setting grid produced zero eligible
  settings. Its best eight-link candidate measured 6/8 correct, while a 6/7
  candidate missed the fixed evidence floor by one. A disclosed S01/S03-only
  refinement added similarity 0.675 and margin 0.02 boundaries without changing
  either gate. Four of 720 final settings passed.
- **Frozen selection:** the selected pure trained Re-ID descriptor has HSV weight
  0, similarity threshold 0.675, margin 0, and maximum gap 45 seconds. It measured
  7/8 correct evaluable development links (0.875), 14 unknown relevant links,
  pairwise precision 10/11 (0.9091), pairwise recall 10/22 (0.4545), F1 0.6061,
  and a four-camera fully scored consistent maximum. S03 contributes only one
  evaluable selected link, so its apparent 1/1 precision has a very small
  denominator.
- **Freeze before diagnostic:** source, config, windows, development mappings,
  model, and selected policy hashes were frozen before creating new S04 or S05
  predictions. Both prediction sets were written before either new evaluation
  call. S04 and S05 were already consumed and remain explicitly post-hoc.
- **Explainable runtime output:** every accepted link retains independent RoadEye
  ID, causal crop hashes, component cosine evidence, threshold, ambiguity margin,
  temporal gap, distance, and topology decision. Prediction generation opens no
  CityFlow identity file.

## FAIL

- **Six-camera journey:** neither post-hoc scenario produced a fully scored,
  identity-consistent group across six cameras. S04's raw maximum is 16 predicted
  cameras, but its consistent maximum is two and it has 20 mixed-identity groups.
  S05's raw maximum is eight, but its consistent maximum is two and it has 26
  mixed-identity groups. The core criterion remains **FAIL**.
- **Transfer precision:** S04 measured 35/50 correct evaluable links (0.7000), 147
  unknown links, pairwise precision 66/154 (0.4286), and recall 66/435 (0.1517)
  over all mappable baseline tracklets. S05 measured 26/45 correct evaluable links
  (0.5778), 498 unknown links, pairwise precision 42/83 (0.5060), and recall
  42/647 (0.0649). These are weak post-hoc diagnostics, not accuracy claims.

## UNVERIFIED

- A fresh held-out six-camera result remains unavailable. Every locally labeled
  scenario has been consumed, and local S06 data has no released GT.
- Exact generalization outside these local CityFlow slices and upstream MTSC
  causality remain unverified.
- Astra 6/xhigh remains unverified because this host exposes no session model or
  reasoning-setting evidence.

## Coverage and limitations

S04 embedded 649/1,723 baseline tracklets and recovered 181/310 labeled camera
visits. S05 reused 2,272/6,609 embedded tracklets and recovered 403/802 visits.
S04 cameras c032 and c040 had especially low causal crop acceptance. Partial
identity labels leave most accepted links unknown, never presumed correct. The
selected HSV weight is zero because color did not improve the development gate.

The strongest next improvement is a new training/development source covering
the severe S04/S05 camera-domain shift: S05 causal appearance retrieval remains
51/254 rank-1 (0.2008). Any further S04/S05 adjustment would be post-hoc tuning
and cannot repair held-out status. The product demo remains the frozen S02
three-camera prediction with a clearly disclosed two-camera verified maximum.

## Verification

- `python -m pytest -q`: PASS, 64 tests.
- `python -m ruff check .`: PASS.
- `python -m pip check`: PASS.
- Prediction-only deterministic replay: PASS for all 649 S04 and 2,272 S05
  assignments; all assignment, link, decision, and journey JSON values matched.
- S04/S05 prediction hashes were written before evaluation and are recorded in
  their ignored `run.json` files. The tracked post-hoc report binds the frozen
  selection hash and measured evaluation results.
