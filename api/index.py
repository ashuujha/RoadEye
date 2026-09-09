"""Vercel entrypoint for the read-only RoadEye evaluation API."""

from __future__ import annotations

import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from roadeye.auth import (  # noqa: E402
    DEMO_PASSWORD_ENV,
    MINIMUM_PASSWORD_LENGTH,
    SignedCookieAuthService,
)
from roadeye.demo import create_app  # noqa: E402


def _create_vercel_app() -> FastAPI:
    password = os.environ.get(DEMO_PASSWORD_ENV, "")
    if len(password) >= MINIMUM_PASSWORD_LENGTH:
        return create_app(
            ROOT / "deployment" / "demo.json",
            auth_service=SignedCookieAuthService(password),
        )

    unavailable = FastAPI(title="RoadEye deployment configuration")

    @unavailable.get("/v1/health/ready")
    def health() -> None:
        raise HTTPException(
            status_code=503,
            detail=f"Set {DEMO_PASSWORD_ENV} to at least {MINIMUM_PASSWORD_LENGTH} characters",
        )

    @unavailable.post("/v1/auth/login")
    def login() -> None:
        raise HTTPException(
            status_code=503,
            detail=f"Set {DEMO_PASSWORD_ENV} in the Vercel project environment",
        )

    return unavailable


app = _create_vercel_app()


@app.middleware("http")
async def normalize_vercel_function_path(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Accept both preserved rewrite paths and Vercel's /api function path."""

    if request.scope["path"].startswith("/api/v1/"):
        request.scope["path"] = request.scope["path"][4:]
        raw_path = request.scope.get("raw_path")
        if isinstance(raw_path, bytes) and raw_path.startswith(b"/api/v1/"):
            request.scope["raw_path"] = raw_path[4:]
    return await call_next(request)
