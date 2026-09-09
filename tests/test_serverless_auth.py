"""Behavior checks for deployment-safe signed demo sessions."""

from roadeye.auth import SignedCookieAuthService


def test_signed_session_is_valid_across_service_instances() -> None:
    clock = [100.0]
    password = "deployment-test-password"
    issuer = SignedCookieAuthService(password, now=lambda: clock[0], ttl_seconds=60)
    verifier = SignedCookieAuthService(password, now=lambda: clock[0], ttl_seconds=60)

    result = issuer.login("administrator", password)

    assert result is not None
    token, issued = result
    assert verifier.authenticate(token) == issued


def test_signed_session_rejects_tampering_and_expiry() -> None:
    clock = [100.0]
    service = SignedCookieAuthService(
        "deployment-test-password",
        now=lambda: clock[0],
        ttl_seconds=60,
    )
    result = service.login("viewer", "deployment-test-password")
    assert result is not None
    token, _session = result

    assert service.authenticate(f"{token}x") is None
    assert service.authenticate("not-base64.%%%") is None
    clock[0] = 161.0
    assert service.authenticate(token) is None
