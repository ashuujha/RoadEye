# Agent instructions

Read `prd.md`, `agents.md`, `plan.md`, and `architecture.md` first. Preserve the 56 hands-on hour/four-calendar-day budget, CPU-only demo, crop-to-journey moment, provenance, and ground-truth isolation. Until feasibility is explicitly cleared, only packaging/environment scaffolding and dataset inspection tooling are allowed; no embeddings, association, pipeline, model, or API implementation.

Use Python 3.11, typed module boundaries, pathlib, small functions, structured logging, snake_case, deterministic seeds, pinned dependencies, and no hidden startup downloads. Do not access real user data, production configuration, or frontends outside `test_frontend/`. Never commit raw datasets, credentials, weights, crops, or databases. Preserve dataset licenses and redaction rules. Findings must be PASS, FAIL, or UNVERIFIED; missing evidence is never PASS. Stop for user direction if CityFlow maximum coverage is below six or Indian data lacks transcriptions and an honest reduced benchmark.

Layout: `src/roadeye/` future modules; `scripts/` inspection and later portable jobs; `configs/`; `tests/`; ignored `data/` and `artifacts/`; `reports/`; `test_frontend/`.

Environment: `py -3.11 -m venv .venv`; use `.venv\\Scripts\\python.exe`; install `requirements-cpu.txt` then editable package. Future commands (`audit`, `prepare`, `evaluate`, `serve`) are not claims that those modules exist. No module is done without provenance, meaningful tests, failure handling, and CPU/offline rehearsal.

