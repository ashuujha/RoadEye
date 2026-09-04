# Contributing

Use a dedicated local branch and small reviewed changes. Python 3.12, uv.lock and package-lock.json define the environment. Run backend Ruff/mypy/tests and frontend types/tests/build. Use actual PostgreSQL/PostGIS for integration; never substitute SQLite. New API schemas require `make generate` and both generated snapshots in the commit.

Use isolated synthetic runs. Preserve raw evidence and machine output, add corrections as revisions, and document policy changes. Do not put secrets, runtime evidence, database files, dependency folders or build outputs in Git. Keep ground-truth fixtures unavailable to runtime code. Scope tests to a failure risk rather than reproducing implementation details.

Before a PR, update requirement-to-test mapping and measured validation report. Hosted CI and Compose verification must be distinguished from native local checks. No deployment or publishing workflow is included. No license was chosen by this implementation; obtain owner direction before redistribution or adding a legal grant.
