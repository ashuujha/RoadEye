"""Dependency-free local authentication for the read-only RoadEye demo."""

from __future__ import annotations

import binascii
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal

Actor = Literal["viewer", "investigator", "administrator", "approver"]

COOKIE_NAME: Final = "roadeye_session"
DEMO_PASSWORD_ENV: Final = "ROADEYE_DEMO_PASSWORD"
MINIMUM_PASSWORD_LENGTH: Final = 16
SESSION_TTL_SECONDS: Final = 8 * 60 * 60


@dataclass(frozen=True)
class AuthSession:
    """Authenticated local actor and the server-side expiry instant."""

    actor: Actor
    expires_at: float


class LocalAuthService:
    """Issue opaque demo sessions while retaining only token digests."""

    def __init__(
        self,
        password: str,
        *,
        now: Callable[[], float] = time.time,
        ttl_seconds: int = SESSION_TTL_SECONDS,
    ) -> None:
        if len(password) < MINIMUM_PASSWORD_LENGTH:
            raise ValueError(
                f"{DEMO_PASSWORD_ENV} must contain at least "
                f"{MINIMUM_PASSWORD_LENGTH} characters"
            )
        if ttl_seconds <= 0:
            raise ValueError("Session lifetime must be positive")
        self._password = password.encode("utf-8")
        self._now = now
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, AuthSession] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> "LocalAuthService":
        password = os.environ.get(DEMO_PASSWORD_ENV)
        if password is None:
            raise ValueError(
                f"{DEMO_PASSWORD_ENV} is required and must contain at least "
                f"{MINIMUM_PASSWORD_LENGTH} characters"
            )
        return cls(password)

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _cleanup_locked(self, now: float) -> None:
        expired = [
            digest
            for digest, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for digest in expired:
            del self._sessions[digest]

    def login(self, actor: Actor, password: str) -> tuple[str, AuthSession] | None:
        """Return a new opaque token and session after a constant-time check."""

        password_matches = hmac.compare_digest(
            self._password, password.encode("utf-8")
        )
        now = self._now()
        session = AuthSession(actor=actor, expires_at=now + self._ttl_seconds)
        with self._lock:
            self._cleanup_locked(now)
            if not password_matches:
                return None
            while True:
                token = secrets.token_urlsafe(32)
                digest = self._digest(token)
                if digest not in self._sessions:
                    self._sessions[digest] = session
                    return token, session

    def authenticate(self, token: str | None) -> AuthSession | None:
        """Resolve an unexpired opaque token without retaining its raw value."""

        now = self._now()
        with self._lock:
            self._cleanup_locked(now)
            if not token:
                return None
            return self._sessions.get(self._digest(token))

    def logout(self, token: str | None) -> None:
        """Invalidate a token when present and opportunistically purge expiry."""

        now = self._now()
        with self._lock:
            self._cleanup_locked(now)
            if token:
                self._sessions.pop(self._digest(token), None)


class SignedCookieAuthService(LocalAuthService):
    """Stateless demo sessions that remain valid across serverless instances."""

    def __init__(
        self,
        password: str,
        *,
        now: Callable[[], float] = time.time,
        ttl_seconds: int = SESSION_TTL_SECONDS,
    ) -> None:
        super().__init__(password, now=now, ttl_seconds=ttl_seconds)
        self._signing_key = hashlib.sha256(
            b"roadeye-serverless-session\0" + password.encode("utf-8")
        ).digest()

    @classmethod
    def from_environment(cls) -> "SignedCookieAuthService":
        password = os.environ.get(DEMO_PASSWORD_ENV)
        if password is None:
            raise ValueError(
                f"{DEMO_PASSWORD_ENV} is required and must contain at least "
                f"{MINIMUM_PASSWORD_LENGTH} characters"
            )
        return cls(password)

    @staticmethod
    def _encode(value: bytes) -> str:
        return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return urlsafe_b64decode(value + padding)

    def login(self, actor: Actor, password: str) -> tuple[str, AuthSession] | None:
        if not hmac.compare_digest(self._password, password.encode("utf-8")):
            return None
        session = AuthSession(
            actor=actor,
            expires_at=self._now() + self._ttl_seconds,
        )
        payload = json.dumps(
            [session.actor, session.expires_at, secrets.token_urlsafe(16)],
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.digest(self._signing_key, payload, "sha256")
        return f"{self._encode(payload)}.{self._encode(signature)}", session

    def authenticate(self, token: str | None) -> AuthSession | None:
        if not token:
            return None
        try:
            encoded_payload, encoded_signature = token.split(".", maxsplit=1)
            payload = self._decode(encoded_payload)
            signature = self._decode(encoded_signature)
            expected = hmac.digest(self._signing_key, payload, "sha256")
            if not hmac.compare_digest(signature, expected):
                return None
            actor, expires_at, _nonce = json.loads(payload)
            if actor not in {"viewer", "investigator", "administrator", "approver"}:
                return None
            session = AuthSession(actor=actor, expires_at=float(expires_at))
            return session if session.expires_at > self._now() else None
        except (binascii.Error, TypeError, ValueError, UnicodeDecodeError):
            return None

    def logout(self, token: str | None) -> None:
        """The response clears the cookie; signed tokens expire automatically."""

        del token
