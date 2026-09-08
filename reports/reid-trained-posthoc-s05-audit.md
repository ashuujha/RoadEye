# Trained Re-ID calibration and S05 post-hoc audit

## Checkpoint status

- **PASS — split boundary:** association settings were selected from an
  identity-disjoint S01 development subset. S02, S04, and S05 identities or
  associations were not opened before the selected policy and runtime source
  hashes were frozen.
- **PASS — runtime integrity:** cached CPU inference completed with ground-truth
  and network access blocked. All 6,816 evidence crop hashes, all 113 link
  evidence cutoffs, deterministic prediction hashes, and three sampled encoder
  outputs were verified. Encoder replay had a maximum absolute error of 0.0.
- **FAIL — six-camera journey:** S05's largest prediction spans five cameras and
  its largest fully scored, single-identity group spans two. No six-camera
  journey is claimed or placed in the demo.
- **UNVERIFIED — unscored associations:** 99 of 113 predicted links cannot be
  assigned a correctness label under the released partial CityFlow annotations.
  They remain unknown rather than being counted as correct or incorrect.
- **UNVERIFIED — fresh held-out generalization:** S05 was consumed before this
  checkpoint. This result is a disclosed post-hoc diagnostic and cannot be
  described as a new held-out benchmark.

## Development-only calibration

The accepted CityFlow-trained encoder was retained unchanged. Thirty declared
association configurations were scored using the 19 S01 identities assigned to
the private bundle's development partition, with all other runtime tracklets left
in place as distractors. Two candidates passed the minimum five-evaluable-link
and 0.80 link-precision gate.

The frozen selection uses cosine similarity 0.65, ambiguity margin 0.10, and a
45-second maximum gap. Among development links touching the selected identities,
5/6 evaluable links were correct, four were unscored, and pairwise precision,
recall, and F1 were 1.0000, 0.4000, and 0.5714 respectively. The longest fully
scored consistent development group covered three cameras. These small,
development-only denominators are configuration-selection evidence, not test
accuracy.

## S05 post-hoc result

The first synchronized 180 seconds of S05 contain 6,609 baseline tracklets and
570,113 baseline observations. The quality-prefix policy accepted 2,272
tracklets using 6,816 crops and produced 2,159 RoadEye global IDs with 113 links.
The largest predicted group spans five cameras.

The offline evaluator mapped 473 baseline tracklets, marked 464 ambiguous, and
left 5,672 unmatched. It recovered 403/802 released GT camera visits. Of 113
links, 14 were evaluable: seven correct and seven incorrect, for 0.5000 precision
on that evaluable subset and 0.1239 evaluation coverage. Pairwise global-ID
precision was 12/20 = 0.6000; recall was 12/507 = 0.0237 among embedded labeled
tracklets and 12/647 = 0.0185 over all mappable baseline tracklets. Causal
appearance retrieval measured rank-1 51/254 = 0.2008 and mAP 0.2258.

Group evaluation counted 356 fully scored consistent groups, 38 partially
scored groups, seven mixed-identity groups, and 1,758 unscored groups. The
fully scored consistent maximum covers two cameras. The three five-camera
predictions all contain ambiguous or unmatched members; none is a verified
five-camera journey.

## Error evidence and next repair

Pair-level topology kept an admissible positive for 241/254 labeled queries;
only 13 lost every positive to constraints. Only 42/254 had an admissible true
match above the selected similarity threshold. This makes cross-scenario
appearance robustness and the representation/score distribution the dominant
failure, while topology is a smaller contributor under this diagnostic.

No S05-driven retuning was performed. A future Re-ID repair needs a new
predeclared development protocol with broader S01/S03 coverage, stronger
camera-aware augmentation or metric learning, and a genuinely unused evaluation
partition or additional approved dataset. It must not present another S05 pass as
fresh held-out evidence.

## Feasibility inspector cleanup

The previously untracked `scripts/feasibility_cityflow.py` now resolves the
dataset beneath `data/cityflow/`. Its rerun measured 65 camera instances, 46
distinct camera IDs, 59 GT files, 253,374 GT rows, and an S04 released identity
spanning 24 cameras. It found no malformed GT rows and reproduced
`configs/feasibility-window.json` byte-for-byte.

## Evidence files

- `reports/reid-trained-association-calibration.json`
- `reports/reid-trained-association-selection.json`
- `reports/reid-trained-posthoc-s05-metrics.json`
- `reports/reid-trained-posthoc-s05-integrity.json`
- `reports/reid-trained-posthoc-s05-error-analysis.json`
