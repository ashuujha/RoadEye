# Agent instructions

## Required model and reasoning

- For all implementation/building work, use **Astra 6 (`gpt-6-astra`) with `xhigh` reasoning**.
- Do not switch to a lower-reasoning model unless the user explicitly requests it.
- Verify the active session configuration when it is exposed. A repository instruction does not itself change the model or reasoning setting. If the setting cannot be verified or changed through available controls, state that limitation; never claim a switch occurred without evidence.
- This requirement does not authorize delegation. Use sub-agents only when explicitly requested by the user or applicable instructions.

## Required phase workflow

1. Verify current repository state, engineering documents, tests, artifacts, commit history, and any supplied Claude context.
2. Fix foundation issues first, within the authorized scope; do not rebuild or redesign working components.
3. Use Plan Mode for the next phase. Session mode is controlled by the host; do not claim to have entered Plan Mode unless it is active.
4. Execute only the approved phase.
5. Audit actual measured results: completed, verified, unverified, failed, metrics, tests, files changed, deviations, and the recommended next phase. Missing evidence remains unverified.
6. Commit locally at each meaningful checkpoint, including each phase end and substantive status handoff. State the phase/hour range and the verified or built change in the commit message. Never push or configure a remote; the user will push later.
7. Stop at each phase checkpoint, or after roughly a few hours of hands-on work, whichever comes first. Report the latest local commit and intended next work, then wait for explicit user direction before continuing.

Read `prd.md`, `agents.md`, `plan.md`, and `architecture.md` first. Preserve the 56 hands-on hour/four-calendar-day budget, CPU-only demo, crop-to-journey moment, provenance, and ground-truth isolation. Until feasibility is explicitly cleared, only packaging/environment scaffolding and dataset inspection tooling are allowed; no embeddings, association, pipeline, model, or API implementation.

Use Python 3.11, typed module boundaries, pathlib, small functions, structured logging, snake_case, deterministic seeds, pinned dependencies, and no hidden startup downloads. Do not access real user data, production configuration, or frontends outside `test_frontend/`. Never commit raw datasets, credentials, weights, crops, or databases. Preserve dataset licenses and redaction rules. Findings must be PASS, FAIL, or UNVERIFIED; missing evidence is never PASS. Stop for user direction if CityFlow maximum coverage is below six or Indian data lacks transcriptions and an honest reduced benchmark.

Layout: `src/roadeye/` future modules; `scripts/` inspection and later portable jobs; `configs/`; `tests/`; ignored `data/` and `artifacts/`; `reports/`; `test_frontend/`.

Environment: `py -3.11 -m venv .venv`; use `.venv\\Scripts\\python.exe`; install `requirements-cpu.txt` then editable package. `python -m roadeye serve --config configs/demo.json` now runs the prediction-only local test interface; the planned `audit`, `prepare`, and `evaluate` top-level commands are still future contracts. No module is done without provenance, meaningful tests, failure handling, and CPU/offline rehearsal.

The approved training-only Re-ID job is built with
`.venv\\Scripts\\python.exe scripts/build_reid_training_bundle.py` and
`.venv\\Scripts\\python.exe scripts/package_reid_colab_job.py`. Its two ZIP files
under `artifacts/reid-training/` are private ignored artifacts; never commit or
redistribute the CityFlow-derived data bundle. Run
`notebooks/roadeye_reid_colab.ipynb` only in a private GPU runtime. A returned
model is not accepted until its manifest/hash, development history, and local
CPU loading are verified. Never copy S01/S03 identities or associations into a
runtime config or demo artifact.

The accepted trained artifact and frozen S02 result are documented in
`reports/reid-trained-model.json` and `reports/reid-trained-s02-audit.md`. S02 is
now consumed. Never tune on S02 or present a later S02 variant as fresh held-out
evidence. The current verified maximum remains two cameras; the three-camera
predicted maximum includes unscored evidence and is not a verified journey.

The hours 27–33 interface is documented in `reports/frontend-audit.md`. Keep its
runtime artifact allowlist free of evaluator mappings and CityFlow identities.
Preserve the local Leaflet bundle and the observed/interpolated, approximate-position,
and uncalibrated-score labels. Plate search and analytics are not implemented yet.
