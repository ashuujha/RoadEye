FROM ghcr.io/astral-sh/uv:0.12.1 AS uv
FROM python:3.12.10-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
COPY migrations ./migrations
COPY alembic.ini ./
COPY data/synthetic/manifest.json data/synthetic/cameras.json data/synthetic/graph.json ./data/synthetic/
COPY data/synthetic/scenarios ./data/synthetic/scenarios
COPY data/synthetic/evidence ./data/synthetic/evidence
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --uid 10001 --create-home roadeye
USER roadeye
