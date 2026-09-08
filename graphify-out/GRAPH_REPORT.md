# Graph Report - RoadEye  (2026-09-08)

## Corpus Check
- 118 files · ~145,168 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 570 nodes · 1205 edges · 27 communities (24 shown, 3 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- ANPR Pipeline
- Phase 2 Tracklets
- ReID Training Encoder
- Association Evaluation Tests
- Architecture Requirements Roadmap
- Demo API Backend
- Leaflet Vendor Cluster A
- Frontend Journey Interface
- Graphify Tooling
- Association Calibration
- Leaflet Vendor Cluster B
- Trained ReID Evaluation
- Leaflet Vendor Cluster C
- Phase 2 Evidence Audit
- OCR Review Protocol
- Frozen S02 Acceptance
- Leaflet Vendor Cluster D
- Leaflet Vendor Cluster E
- ANPR Integrity Audit
- ReID Bundle Builder
- Leaflet Vendor Cluster F
- Baseline ReID Audit
- Frontend Evidence Audit
- CityFlow Feasibility Inspection
- Leaflet Vendor Cluster G
- RoadEye Package Metadata
- Project Packaging

## God Nodes (most connected - your core abstractions)
1. `sha256()` - 52 edges
2. `write_json()` - 39 edges
3. `DemoRepository` - 18 edges
4. `Observation` - 18 edges
5. `associate()` - 16 edges
6. `evaluate()` - 16 edges
7. `text_sha256()` - 15 edges
8. `main()` - 14 edges
9. `obs()` - 14 edges
10. `graphify` - 14 edges

## Surprising Connections (you probably didn't know these)
- `test_recall_counts_tracks_excluded_by_quality_filter()` --calls--> `association_metrics()`  [INFERRED]
  tests/test_reid_improvement.py → src/roadeye/evaluation.py
- `test_vehicle_checkpoint_corruption_is_rejected_before_loading()` --calls--> `load_vehicle_encoder()`  [INFERRED]
  tests/test_reid_improvement.py → src/roadeye/vehicle_encoder.py
- `Graph health` --semantically_similar_to--> `Trained encoder acceptance`  [INFERRED] [semantically similar]
  .codex/skills/graphify/SKILL.md → architecture.md
- `Confidence taxonomy` --semantically_similar_to--> `Independent accuracy claims`  [INFERRED] [semantically similar]
  .codex/skills/graphify/references/extraction-spec.md → prd.md
- `Graph-first navigation` --semantically_similar_to--> `CLAUDE integration`  [INFERRED] [semantically similar]
  agents.md → .codex/skills/graphify/references/hooks.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Frozen prediction evidence flow** — architecture_frozen_s02_predictions, architecture_read_only_evidence_api, test_frontend_readme_test_frontend, test_frontend_index_journey_replay, test_frontend_index_source_evidence [EXTRACTED 1.00]
- **Training acceptance boundary** — architecture_training_identity_split, architecture_private_training_job, architecture_trained_encoder_acceptance, agents_ground_truth_isolation [EXTRACTED 1.00]
- **Sealed OCR evaluation** — agents_manual_transcription_gate, architecture_reviewed_transcription_truth, architecture_ocr_preprocessing, plan_anpr_checkpoint [EXTRACTED 1.00]
- **Human development review precedes OCR variant freezing and sealed test scoring** — reports_anpr_transcription_runbook_development_review, reports_anpr_transcription_runbook_freeze_ocr, reports_anpr_transcription_runbook_sealed_test_scoring [EXTRACTED 1.00]
- **Private training transfer, verified return, and frozen evaluation form the model acceptance workflow** — reports_reid_training_runbook_private_artifact_transfer, reports_reid_training_runbook_returned_artifact_acceptance, reports_reid_training_runbook_frozen_evaluation_gate [EXTRACTED 1.00]
- **Partial released labels constrain every measured multi-camera journey claim** — reports_phase2_runbook_partial_label_metrics, reports_phase2_audit_s04_diagnostic, reports_reid_audit_original_s05_result, reports_reid_trained_s02_audit_frozen_s02_result, reports_reid_trained_posthoc_s05_audit_s05_result, reports_frontend_audit_frozen_s02_demo_limit [INFERRED 0.95]

## Communities (27 total, 3 thin omitted)

### Community 0 - "ANPR Pipeline"
Cohesion: 0.07
Nodes (78): main(), main(), audit(), build_detector(), build_review(), _detector_predictions(), evaluate(), evaluate_detector() (+70 more)

### Community 1 - "Phase 2 Tracklets"
Cohesion: 0.05
Nodes (60): freeze_window(), main(), Path, Freeze clock-selected comparison windows using metadata only, never GT., Freeze the accepted trained model and S02 runtime inputs before GT scoring., Package only the code/config needed by the private Colab training job., Compatibility entry point for the Phase 2 command., guard() (+52 more)

### Community 2 - "ReID Training Encoder"
Cohesion: 0.05
Nodes (41): main(), Run the RoadEye training-only Re-ID job on a CUDA machine/Colab., main(), Path, Prove that a RoadEye Re-ID export reloads and infers on CPU exactly., Round-trip the real architecture and compare deterministic CPU outputs., verify(), batch_hard_triplet_loss() (+33 more)

### Community 3 - "Association Evaluation Tests"
Cohesion: 0.08
Nodes (50): parametrize, analyze(), main(), Path, Offline diagnostic: separate pair-level gate losses from appearance failures.…, develop(), initialize(), main() (+42 more)

### Community 4 - "Architecture Requirements Roadmap"
Cohesion: 0.06
Nodes (46): Confidence taxonomy, Graph health, CPU offline contract, Ground-truth isolation, Manual transcription gate, Phase workflow, Approximate camera topology, Causal prefix (+38 more)

### Community 5 - "Demo API Backend"
Cohesion: 0.11
Nodes (27): Any, FastAPI, MonkeyPatch, _bearing_degrees(), create_app(), DemoPaths, DemoRepository, _json() (+19 more)

### Community 6 - "Leaflet Vendor Cluster A"
Cohesion: 0.08
Nodes (6): a(), Ci(), l(), me(), x(), ze()

### Community 7 - "Frontend Journey Interface"
Cohesion: 0.19
Nodes (22): cameraLayer, drawCameras(), elements, figure(), getJson(), loadVehicles(), map, markerIcon() (+14 more)

### Community 8 - "Graphify Tooling"
Cohesion: 0.16
Nodes (19): URL ingestion, Watch mode, Graph exports, MCP server, Deterministic node IDs, Cross-repository graphs, CLAUDE integration, Post-commit hook (+11 more)

### Community 9 - "Association Calibration"
Cohesion: 0.22
Nodes (13): calibrate(), _development_identities(), development_metrics(), _freeze_posthoc(), main(), posthoc(), Path, Calibrate association on private S01 development IDs, then freeze S05 post-hoc. (+5 more)

### Community 10 - "Leaflet Vendor Cluster B"
Cohesion: 0.19
Nodes (13): bi(), c(), e(), hi(), m(), Pi(), Qe(), Ti() (+5 more)

### Community 11 - "Trained ReID Evaluation"
Cohesion: 0.24
Nodes (12): Generic appearance discrimination identified as primary Phase 2 improvement target, Official FastReID VeRi SBS ResNet-50-IBN CPU encoder and upstream parity, Cross-scenario appearance robustness dominates post-hoc S05 failure, Trained Re-ID calibration and S05 post-hoc audit, Future Re-ID repair requires broader development and an unused evaluation partition, S01 development calibration selects similarity 0.65, ambiguity margin 0.10, and 45-second gap, Trained post-hoc S05: 113 links, 7/14 scored correct, five predicted cameras, two verified, Versioned RoadEye encoder export reloads exactly through production CPU loader (+4 more)

### Community 12 - "Leaflet Vendor Cluster C"
Cohesion: 0.24
Nodes (12): F(), G(), h(), j(), k(), ke(), ne(), e() (+4 more)

### Community 13 - "Phase 2 Evidence Audit"
Cohesion: 0.22
Nodes (11): OCR accuracy remains UNVERIFIED until human transcription and frozen selection, CityFlow hard gate PASS: S04 identity 260 spans 24 cameras, Local Leaflet map and timeline distinguish observed times, approximate positions, and interpolation, Calibration-derived proximity and time gates with approximate geographic provenance, Phase 2 foundation repair audit, hours 10–18, Ground-truth reads moved entirely into separately invoked evaluator, S04 repaired diagnostic: 60 links, 6/10 scored correct, four predicted cameras, two verified, Phase 2 CPU baseline and evidence runbook (+3 more)

### Community 14 - "OCR Review Protocol"
Cohesion: 0.25
Nodes (11): Human development review: all 50 families terminal, at least 40 readable strings, Indian plate transcription and OCR evaluation runbook, freeze-ocr selects and hashes one preprocessing variant using development truth, Supplied-crop recognition does not establish end-to-end scene ANPR, One-time OCR test scoring: 200 test families with at least 150 readable reviewed strings, Feasibility gate and later ANPR re-audit, Indian benchmark capacity PASS: 200 independent test crops and 50 development crops, Indian transcription availability FAIL: supplied annotations contain boxes only (+3 more)

### Community 15 - "Frozen S02 Acceptance"
Cohesion: 0.22
Nodes (11): Frozen demo: 1,503 RoadEye IDs, 37 links, three predicted cameras, at most two verified, S02 is consumed and cannot select or validate new parameters, Trained encoder development rank-1 improves 67/99 to 87/99; mAP 0.5732 to 0.8829, Returned Re-ID model and frozen S02 audit, hours 24–27, Frozen S02: 37 links, 3/3 scored correct, recall 3/23, three predicted cameras, two verified, Returned Re-ID artifact accepted after ZIP/hash/history checks and Python 3.11 CPU loading, Training environment FAIL: Colab used Python 3.13 and Torch 2.11; local Python 3.11 CPU compatibility PASS, Private CityFlow Re-ID training runbook (+3 more)

### Community 16 - "Leaflet Vendor Cluster D"
Cohesion: 0.22
Nodes (9): Ae(), be(), De(), ei(), Ie(), ii(), p(), pe() (+1 more)

### Community 17 - "Leaflet Vendor Cluster E"
Cohesion: 0.25
Nodes (9): at(), d(), ht(), i(), Li(), Mi(), v(), W() (+1 more)

### Community 18 - "ANPR Integrity Audit"
Cohesion: 0.25
Nodes (8): Development-only review page and enforced OCR test-sealing gate, Indian ANPR checkpoint audit, hours 33–43, EasyOCR development preparation: three preprocessing variants and 150 unscored predictions, ANPR split: 1,098 independent families; 50 development and 200 test plate crops, Cached CPU detector and OCR produce identical outputs with networking blocked, YOLOv8n CPU plate detector: test precision 0.9455, recall 0.8525, F1 0.8966, Phase 2 checksum-linked evidence, predictions, journeys, and separate evaluation artifacts, Frozen Re-ID integrity replay blocks GT/network and checks hashes, prefixes, crops, and CPU descriptors

### Community 19 - "ReID Bundle Builder"
Cohesion: 0.48
Nodes (6): build(), collect(), main(), Path, Build a private, label-bearing S01/S03 crop bundle for the Colab job., spaced()

### Community 20 - "Leaflet Vendor Cluster F"
Cohesion: 0.29
Nodes (7): Jt(), Le(), O(), Qt(), Re(), $t(), te()

### Community 21 - "Baseline ReID Audit"
Cohesion: 0.40
Nodes (6): ImageNet ResNet-50 CPU features from first-three-observation prefixes, Consumed S05 supports disclosed post-hoc comparisons only, Bounded vehicle Re-ID comparison audit, hours 18–21, Original frozen S05: 147 links, 2/4 scored correct, recall 2/647, two verified cameras, Causal quality prefix separates track start, first usable crop, and identity readiness, S01 replacement gate FAIL; frozen fallback retains ImageNet with similarity 0.85 and margin 0.03

### Community 22 - "Frontend Evidence Audit"
Cohesion: 0.83
Nodes (4): Crop-to-journey interaction with three causal appearance samples and exact source frames, Local evidence interface audit, hours 27–33, roadeye.demo read-only API serves frozen S02 artifacts, Runtime artifact allowlist excludes evaluator mappings and CityFlow identities

### Community 24 - "Leaflet Vendor Cluster G"
Cohesion: 0.67
Nodes (4): Je(), ni(), oi(), si()

## Knowledge Gaps
- **19 isolated node(s):** `roadeeye`, `state`, `elements`, `map`, `cameraLayer` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 126 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sha256()` connect `ANPR Pipeline` to `Phase 2 Tracklets`, `ReID Training Encoder`, `Association Evaluation Tests`, `Association Calibration`, `ReID Bundle Builder`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `write_json()` connect `ANPR Pipeline` to `Phase 2 Tracklets`, `ReID Training Encoder`, `Association Evaluation Tests`, `Association Calibration`, `ReID Bundle Builder`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `train()` connect `ReID Training Encoder` to `ANPR Pipeline`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `DemoRepository` (e.g. with `test_catalog_search_and_evidence_labels()` and `test_changed_prediction_fails_before_catalog_load()`) actually correct?**
  _`DemoRepository` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Observation` (e.g. with `analyze()` and `develop()`) actually correct?**
  _`Observation` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `roadeeye`, `state`, `elements` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ANPR Pipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.0669753086419753 - nodes in this community are weakly interconnected._