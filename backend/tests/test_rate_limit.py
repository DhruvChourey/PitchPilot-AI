"""Rate-limit tests for login/register. Uses the real `pitchpilot_test`
schema/role like every other DB-backed test file -- no mocking of the
HTTP layer, only the limiter's clock, so behavior is deterministic
without real sleeps.

The autouse `_reset_rate_limits` fixture in conftest.py already clears
all buckets before each test; these tests additionally monkeypatch each
limiter's `.clock` attribute directly to control elapsed time.
"""

import uuid

from app.config import settings
from app.core import rate_limit as rate_limit_module
from tests.conftest import fetch_preauth_csrf_token


def _unique_email() -> str:
    return f"ratelimit-{uuid.uuid4().hex[:10]}@example.com"


def _set_fake_clock(monkeypatch, *limiters, now: list[float]):
    for limiter in limiters:
        monkeypatch.setattr(limiter, "clock", lambda: now[0])


def test_login_ip_limit_returns_429_after_threshold(client, monkeypatch):
    # The `client` fixture's own setup already performed one real login,
    # which counted against these same module-level limiters -- reset
    # again here, after fixture setup, so the loop below counts cleanly.
    rate_limit_module.reset_all_rate_limits()
    now = [0.0]
    _set_fake_clock(
        monkeypatch, rate_limit_module.login_ip_limiter, rate_limit_module.login_email_limiter, now=now
    )
    rule = rate_limit_module.LOGIN_IP_RULE
    # `client` already consumed its pre-auth cookie during its own
    # fixture login; a failed login (wrong password) never issues a new
    # one, so fetching it once up front is enough for the whole loop.
    fetch_preauth_csrf_token(client)

    # Distinct emails per attempt so only the per-IP limiter (not the
    # per-email one) is what trips here.
    for _ in range(rule.max_requests):
        response = client.post(
            "/api/v1/auth/login", json={"email": _unique_email(), "password": "wrong-password"}
        )
        assert response.status_code == 401  # wrong password, but not rate-limited yet

    over_limit_response = client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "wrong-password"}
    )

    assert over_limit_response.status_code == 429
    assert "Retry-After" in over_limit_response.headers


def test_login_email_limit_is_independent_of_ip_limit(client, monkeypatch):
    now = [0.0]
    _set_fake_clock(
        monkeypatch, rate_limit_module.login_ip_limiter, rate_limit_module.login_email_limiter, now=now
    )
    email = _unique_email()
    rule = rate_limit_module.LOGIN_EMAIL_RULE
    assert rule.max_requests < rate_limit_module.LOGIN_IP_RULE.max_requests
    fetch_preauth_csrf_token(client)

    for _ in range(rule.max_requests):
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
        assert response.status_code == 401

    over_limit_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )

    assert over_limit_response.status_code == 429


def test_login_rate_limit_keys_are_distinct_per_email(client, monkeypatch):
    """Exhausting the per-email limit for one email must not affect a
    different email from the same client/IP."""
    now = [0.0]
    _set_fake_clock(
        monkeypatch, rate_limit_module.login_ip_limiter, rate_limit_module.login_email_limiter, now=now
    )
    exhausted_email = _unique_email()
    rule = rate_limit_module.LOGIN_EMAIL_RULE
    fetch_preauth_csrf_token(client)

    for _ in range(rule.max_requests):
        client.post("/api/v1/auth/login", json={"email": exhausted_email, "password": "wrong-password"})
    blocked_response = client.post(
        "/api/v1/auth/login", json={"email": exhausted_email, "password": "wrong-password"}
    )
    assert blocked_response.status_code == 429

    other_email_response = client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "wrong-password"}
    )
    assert other_email_response.status_code == 401  # not 429 -- independent key


def test_login_rate_limit_resets_after_window_elapses(client, monkeypatch):
    rate_limit_module.reset_all_rate_limits()
    now = [0.0]
    _set_fake_clock(
        monkeypatch, rate_limit_module.login_ip_limiter, rate_limit_module.login_email_limiter, now=now
    )
    rule = rate_limit_module.LOGIN_IP_RULE
    fetch_preauth_csrf_token(client)

    for _ in range(rule.max_requests):
        client.post("/api/v1/auth/login", json={"email": _unique_email(), "password": "wrong-password"})
    blocked_response = client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "wrong-password"}
    )
    assert blocked_response.status_code == 429

    now[0] += rule.window_seconds + 1  # advance the fake clock past the window
    recovered_response = client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "wrong-password"}
    )
    assert recovered_response.status_code == 401  # throttled -> allowed again, not locked out


def test_register_ip_limit_returns_429_after_threshold(db_session, monkeypatch):
    from tests.conftest import _make_test_client

    now = [0.0]
    _set_fake_clock(
        monkeypatch, rate_limit_module.register_ip_limiter, rate_limit_module.register_email_limiter, now=now
    )
    rule = rate_limit_module.REGISTER_IP_RULE
    fresh_client = _make_test_client(db_session)
    fetch_preauth_csrf_token(fresh_client)

    for _ in range(rule.max_requests):
        response = fresh_client.post(
            "/api/v1/auth/register", json={"email": _unique_email(), "password": "test-password-1"}
        )
        assert response.status_code == 201, response.text

    over_limit_response = fresh_client.post(
        "/api/v1/auth/register", json={"email": _unique_email(), "password": "test-password-1"}
    )

    assert over_limit_response.status_code == 429
    assert "Retry-After" in over_limit_response.headers


def test_register_does_not_permanently_lock_out_after_reset(db_session, monkeypatch):
    from tests.conftest import _make_test_client

    now = [0.0]
    _set_fake_clock(
        monkeypatch, rate_limit_module.register_ip_limiter, rate_limit_module.register_email_limiter, now=now
    )
    rule = rate_limit_module.REGISTER_IP_RULE
    fresh_client = _make_test_client(db_session)
    fetch_preauth_csrf_token(fresh_client)

    for _ in range(rule.max_requests):
        fresh_client.post(
            "/api/v1/auth/register", json={"email": _unique_email(), "password": "test-password-1"}
        )
    blocked = fresh_client.post(
        "/api/v1/auth/register", json={"email": _unique_email(), "password": "test-password-1"}
    )
    assert blocked.status_code == 429

    now[0] += rule.window_seconds + 1
    recovered = fresh_client.post(
        "/api/v1/auth/register", json={"email": _unique_email(), "password": "test-password-1"}
    )
    assert recovered.status_code == 201, recovered.text


def test_rate_limiter_keys_never_store_raw_email(monkeypatch):
    """The limiter's internal state must key by a hash, not the raw
    email -- so dumping its state (e.g. in a debugger) can't leak
    submitted emails."""
    limiter = rate_limit_module.RateLimiter()
    rule = rate_limit_module.RateLimitRule(max_requests=5, window_seconds=60)
    raw_email = "someone-sensitive@example.com"

    rate_limit_module._enforce(limiter, rate_limit_module._hash_email(raw_email), rule, "test")

    assert raw_email not in limiter._hits
    assert all(raw_email not in key for key in limiter._hits)
