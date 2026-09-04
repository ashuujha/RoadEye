# Evaluation boundaries

Current executable tests establish deterministic software behavior: conservative normalization, duplicate frame handling, graph hard checks, alternatives, UTC boundaries, PostgreSQL constraints, replay, processing recovery, authorization, evidence integrity and scenario counts. Ground truth is test-only and asserts exact outcomes in `synthetic_scenarios.md`.

They do not measure recognition accuracy, real vehicle identity, real traffic coverage or operational capacity. No percentage achieved is reported for AI performance.

Next-phase evaluation follows `real_data_integration.md`: annotate independent held-out connected footage, avoid adjacent-frame/passage leakage, separately evaluate vehicle counting, full-plate OCR, incorrect accepted readings, rejections, link precision/recall and travel-time error. Break down by camera, lighting, weather, motion, occlusion and plate format. Report denominators, confidence intervals, abstention/coverage tradeoffs and hardware load. Threshold changes require policy-version updates and regression evidence.
