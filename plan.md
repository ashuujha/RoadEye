# 56-hour build plan (four calendar days / 96 elapsed hours)

| Hours | Work | Priority |
|---|---|---|
| 0–2 | Planning and feasibility protocol | Critical |
| 2–10 | Python 3.11 setup; CityFlow and Indian downloads/audit; freeze feasible subsets; evidence report | **Critical gate** |
| 10–18 | CityFlow import, CPU embeddings, association baseline, evaluator | Critical |
| 18–24 | Crop selection, evidence timeline, map, replay | Critical |
| 24–34 | Indian transcription/review, detector/OCR, preprocessing, evaluation | Critical |
| 34–40 | Portable Colab export and bounded Re-ID improvement, if justified | Conditional |
| 40–45 | Plate search, hybrid evidence, OD, density heat map, bottleneck proxies | Required |
| 45–51 | Frozen evaluation, leakage checks, error analysis, CPU timing | Critical |
| 51–56 | Integration repair, offline rehearsal, claims and evidence packaging | Critical |

Hard gates: verify actual CityFlow camera coverage and Indian transcription/test capacity before implementation; stop for user direction on either failure. Never use ground truth at runtime or fabricate journeys. Allow up to 1 hour for Roboflow/IEEE checks, 6 hours for transcription review, and 3 hours for portable setup. Cut extra model variants, supplementary datasets, further tuning, and presentation polish first. Never cut evaluation, provenance, uncertainty, or CPU rehearsal.

## Current checkpoint — Phase 2 repair

The user explicitly approved Phase 2 independently of the Indian OCR gate. The original Phase 2 smoke result did not constitute a valid evaluation; the repaired code now processes the full frozen S04 window, isolates GT, makes causal decisions, and emits measured diagnostic results. See `reports/phase2-audit.md` and `reports/phase2-metrics.json`.

Foundation checks pass, but the six-camera predicted-journey goal is still unmet: the longest fully scored consistent group covers two cameras. Do not silently advance to hours 18–24 or spend the later fine-tuning allocation. Stop for the user's direction on a bounded Re-ID improvement checkpoint and fresh evaluation plan. All future phases retain the local audit/commit/explicit-clearance workflow in `agents.md`.
