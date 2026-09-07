# 56-hour build plan (four calendar days / 96 elapsed hours)

| Hours | Work | Priority |
|---|---|---|
| 0–2 | Planning and feasibility protocol | Critical |
| 2–10 | Python 3.11 setup; CityFlow and Indian downloads/audit; freeze feasible subsets; evidence report | **Critical gate** |
| 10–18 | CityFlow import, CPU embeddings, association baseline, evaluator | Critical |
| 18–21 | User-approved Phase 2 continuation: bounded pretrained vehicle Re-ID comparison and frozen evaluation | Critical repair; 3-hour cap |
| 21–27 | Crop selection, evidence timeline, map, replay | Critical |
| 27–37 | Indian transcription/review, detector/OCR, preprocessing, evaluation | Critical |
| 37–40 | Portable Colab export; fine-tuning only if separately justified and approved | Conditional |
| 40–45 | Plate search, hybrid evidence, OD, density heat map, bottleneck proxies | Required |
| 45–51 | Frozen evaluation, leakage checks, error analysis, CPU timing | Critical |
| 51–56 | Integration repair, offline rehearsal, claims and evidence packaging | Critical |

Hard gates: verify actual CityFlow camera coverage and Indian transcription/test capacity before implementation; stop for user direction on either failure. Never use ground truth at runtime or fabricate journeys. Allow up to 1 hour for Roboflow/IEEE checks, 6 hours for transcription review, and 3 hours for portable setup. Cut extra model variants, supplementary datasets, further tuning, and presentation polish first. Never cut evaluation, provenance, uncertainty, or CPU rehearsal.

## Current checkpoint — Phase 2 repair

The user explicitly approved Phase 2 independently of the Indian OCR gate. The original Phase 2 smoke result did not constitute a valid evaluation; the repaired code now processes the full frozen S04 window, isolates GT, makes causal decisions, and emits measured diagnostic results. See `reports/phase2-audit.md` and `reports/phase2-metrics.json`.

Foundation checks pass, but the six-camera predicted-journey goal is still unmet: the longest fully scored consistent group covers two cameras. Do not silently advance to hours 18–24 or spend the later fine-tuning allocation. Stop for the user's direction on a bounded Re-ID improvement checkpoint and fresh evaluation plan. All future phases retain the local audit/commit/explicit-clearance workflow in `agents.md`.

## Approved Phase 2 continuation

The user's subsequent **go** approves the recommended bounded Re-ID improvement
checkpoint before frontend work. Pull three hours forward from the original
34–40 conditional allocation; keep the total at 56 hands-on hours / 96 elapsed
hours. The table above reflects this allocation, not a claim that all prior
budgeted hours were consumed. No GPU fine-tuning is performed in this checkpoint.

Compare the existing ImageNet encoder, an official VeRi-trained encoder, and a
causal quality-filtered crop prefix on S01 only. Freeze first-180-second windows
without identity labels. Select from the predeclared S01 parameter grid using
minimum link evidence/precision and pairwise F1 whose recall denominator includes
excluded mappable tracklets. Freeze configuration, source hashes and development
results before one S05 evaluation. Preserve S04 results unchanged. Exact protocol:
`configs/reid-experiment.json`. Stop with an audit and local commit; frontend,
OCR, training and subsequent phases require another explicit go-ahead.

### Hours 18–21 outcome

The VeRi encoder passed exact CPU adapter parity and improved S01 labelled-gallery
retrieval, but none of 30 predeclared development configurations met the minimum
evidence/precision gate. The frozen fallback therefore retained the original
ImageNet model and thresholds for one S05 evaluation. S05 measured 2/4 correct
evaluable links, 2/647 pairwise recall, and a longest fully scored consistent
journey of two cameras. The six-camera demo target remains failed even though ten
S05 identities are mappable across at least six cameras. See
`reports/reid-audit.md`. Do not silently tune on consumed S05 or start the next
phase; wait for the user's decision between training-only fine-tuning and the
frontend phase with the current limitation.
