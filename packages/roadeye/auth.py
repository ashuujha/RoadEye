import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from roadeye import models as m
from roadeye.config import settings
from roadeye.contracts import Login
from roadeye.db import now, session


def login(body: Login, response: Response, db: Session) -> dict:
    if not settings.demo_enabled:
        raise HTTPException(404, "LOCAL_AUTH_DISABLED")
    if not hmac.compare_digest(body.password.encode(), settings.demo_password.encode()):
        raise HTTPException(401, "INVALID_CREDENTIALS")
    token = secrets.token_urlsafe(32)
    db.add(
        m.LocalSession(
            digest=hashlib.sha256(token.encode()).hexdigest(),
            actor=body.actor.value,
            expires_at=now() + timedelta(hours=8),
        )
    )
    db.commit()
    response.set_cookie("roadeye_session", token, httponly=True, samesite="strict", max_age=28800)
    return {"actor": body.actor.value, "mode": "local_demo"}


def identity(request: Request, db: Session = Depends(session)) -> str:
    token = request.cookies.get("roadeye_session", "")
    row = db.get(m.LocalSession, hashlib.sha256(token.encode()).hexdigest())
    if not row or row.expires_at <= now():
        raise HTTPException(401, "SESSION_REQUIRED")
    return row.actor


def allow(*roles: str):
    def check(actor: str = Depends(identity)) -> str:
        if actor not in roles:
            raise HTTPException(403, "ROLE_DENIED")
        return actor

    return check


investigator = allow("investigator", "administrator")
admin = allow("administrator")
approver = allow("approver")
