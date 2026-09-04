.PHONY: setup up migrate seed-demo demo test lint typecheck validate down generate client-check browser
setup:
	python3 scripts/setup.py
	uv sync --frozen --python 3.12
	cd apps/web && npm ci
up:
	docker compose up --build -d
migrate:
	uv run alembic upgrade head
seed-demo:
	uv run python -m scripts.demo --scenario normal_journey --no-play
demo:
	uv run python -m scripts.demo --scenario normal_journey
test:
	uv run pytest tests/unit tests/integration
	cd apps/web && npm test
lint:
	uv run ruff check packages apps scripts tests migrations
	uv run ruff format --check packages apps scripts tests migrations
typecheck:
	uv run mypy
	cd apps/web && npm run typecheck
generate:
	uv run python -m scripts.export_openapi
	cd apps/web && npm run generate
client-check: generate
	git diff --exit-code -- packages/roadeye/openapi.json apps/web/src/api.generated.ts
browser:
	uv run python -m scripts.browser
validate: lint typecheck test client-check
	cd apps/web && npm run build
	uv run python -m scripts.e2e
	$(MAKE) browser
down:
	docker compose down
