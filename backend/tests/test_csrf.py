"""CSRF enforcement tests: both token flavors (session-bound and
pre-authentication, see app/core/csrf.py and DECISIONS.md) and the
Origin/Referer policy.

Uses the real-Postgres `client`/`db_session` fixtures from conftest.py --
same isolated pitchpilot_test schema and pitchpilot_test_app role as every
other real-DB test file, never TEST_DATABASE_URL's admin role and never
DATABASE_URL.
"""

import uuid

from app.config import settings
from tests.conftest import _TRUSTED_TEST_ORIGIN, _make_test_client, fetch_preauth_csrf_token


def _lead_payload() -> dict:
    return {
        "company_name": f"CSRF Test Co {uuid.uuid4().hex[:6]}",
        "website": "https://csrf-test.example.com",
        "industry": "Testing",
    }


# ---------------------------------------------------------------------------
# Session-bound CSRF (authenticated lead mutations, logout)
# ---------------------------------------------------------------------------


def test_lead_create_missing_csrf_header_is_rejected(client):
    del client.headers[settings.csrf_header_name]

    response = client.post("/api/v1/leads", json=_lead_payload())

    assert response.status_code == 403


def test_lead_create_missing_csrf_cookie_is_rejected(client):
    client.cookies.delete(settings.csrf_cookie_name)

    response = client.post("/api/v1/leads", json=_lead_payload())

    assert response.status_code == 403


def test_lead_create_cookie_header_mismatch_is_rejected(client):
    response = client.post(
        "/api/v1/leads",
        json=_lead_payload(),
        headers={settings.csrf_header_name: "a-different-value-than-the-cookie"},
    )

    assert response.status_code == 403


def test_lead_create_tampered_csrf_token_is_rejected(client):
    """Cookie and header agree with each other but neither is a value
    this server ever signed -- the equality check alone would pass this;
    the signature check must be what catches it."""
    forged_value = "attacker-forged-token"
    client.cookies.set(settings.csrf_cookie_name, forged_value)

    response = client.post(
        "/api/v1/leads",
        json=_lead_payload(),
        headers={settings.csrf_header_name: forged_value},
    )

    assert response.status_code == 403


def test_lead_create_valid_csrf_succeeds(client):
    response = client.post("/api/v1/leads", json=_lead_payload())

    assert response.status_code == 201, response.text


def test_lead_update_requires_valid_csrf(client):
    create_response = client.post("/api/v1/leads", json=_lead_payload())
    lead_id = create_response.json()["id"]

    del client.headers[settings.csrf_header_name]
    response = client.patch(f"/api/v1/leads/{lead_id}", json={"company_name": "Updated"})

    assert response.status_code == 403


def test_lead_archive_requires_valid_csrf(client):
    create_response = client.post("/api/v1/leads", json=_lead_payload())
    lead_id = create_response.json()["id"]

    del client.headers[settings.csrf_header_name]
    response = client.delete(f"/api/v1/leads/{lead_id}")

    assert response.status_code == 403


def test_logout_missing_csrf_header_is_rejected(client):
    del client.headers[settings.csrf_header_name]

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 403


def test_logout_with_valid_csrf_succeeds(client):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200


def test_csrf_token_rotates_on_login(client, db_session):
    """A second login (same client, same cookie jar) must mint a
    different session-bound CSRF cookie than the first -- it's derived
    from the new session's hashed_token, which is different each login."""
    first_token = client.cookies.get(settings.csrf_cookie_name)
    assert first_token

    second_client = _make_test_client(db_session)
    fetch_preauth_csrf_token(second_client)
    # Log the *same underlying account* in again from a second client to
    # get a second, independent session -- simplest way to get a second
    # real session without logging the first one out.
    email = f"rotate-{uuid.uuid4().hex[:10]}@example.com"
    password = "test-password-1"
    second_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    fetch_preauth_csrf_token(second_client)
    login_response = second_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200, login_response.text

    second_token = second_client.cookies.get(settings.csrf_cookie_name)
    assert second_token
    assert second_token != first_token


# ---------------------------------------------------------------------------
# Origin / Referer policy
# ---------------------------------------------------------------------------


def test_lead_create_missing_origin_and_referer_is_rejected(client):
    del client.headers["origin"]

    response = client.post("/api/v1/leads", json=_lead_payload())

    assert response.status_code == 403


def test_lead_create_mismatched_origin_is_rejected(client):
    response = client.post(
        "/api/v1/leads", json=_lead_payload(), headers={"origin": "https://evil.example.com"}
    )

    assert response.status_code == 403


def test_lead_create_falls_back_to_valid_referer_when_origin_absent(client):
    del client.headers["origin"]

    response = client.post(
        "/api/v1/leads",
        json=_lead_payload(),
        headers={"referer": f"{_TRUSTED_TEST_ORIGIN}/leads/new"},
    )

    assert response.status_code == 201, response.text


def test_lead_create_mismatched_referer_is_rejected(client):
    del client.headers["origin"]

    response = client.post(
        "/api/v1/leads",
        json=_lead_payload(),
        headers={"referer": "https://evil.example.com/leads/new"},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Pre-authentication CSRF (register, login)
# ---------------------------------------------------------------------------


def test_register_without_preauth_token_is_rejected(db_session):
    fresh_client = _make_test_client(db_session)
    # Deliberately never calls GET /auth/csrf-token.

    response = fresh_client.post(
        "/api/v1/auth/register",
        json={"email": f"nopreauth-{uuid.uuid4().hex[:8]}@example.com", "password": "test-password-1"},
    )

    assert response.status_code == 403


def test_login_without_preauth_token_is_rejected(db_session):
    fresh_client = _make_test_client(db_session)

    response = fresh_client.post(
        "/api/v1/auth/login",
        json={"email": f"nopreauth-{uuid.uuid4().hex[:8]}@example.com", "password": "test-password-1"},
    )

    assert response.status_code == 403


def test_register_with_tampered_preauth_token_is_rejected(db_session):
    fresh_client = _make_test_client(db_session)
    fetch_preauth_csrf_token(fresh_client)
    fresh_client.cookies.set(settings.preauth_csrf_cookie_name, "forged.nonsense")
    fresh_client.headers[settings.csrf_header_name] = "forged.nonsense"

    response = fresh_client.post(
        "/api/v1/auth/register",
        json={"email": f"tampered-{uuid.uuid4().hex[:8]}@example.com", "password": "test-password-1"},
    )

    assert response.status_code == 403


def test_register_with_valid_preauth_token_succeeds(db_session):
    fresh_client = _make_test_client(db_session)
    fetch_preauth_csrf_token(fresh_client)

    response = fresh_client.post(
        "/api/v1/auth/register",
        json={"email": f"validpreauth-{uuid.uuid4().hex[:8]}@example.com", "password": "test-password-1"},
    )

    assert response.status_code == 201, response.text


def test_csrf_token_endpoint_does_not_regenerate_an_existing_valid_cookie(db_session):
    fresh_client = _make_test_client(db_session)
    fetch_preauth_csrf_token(fresh_client)
    first_token = fresh_client.cookies.get(settings.preauth_csrf_cookie_name)

    second_response = fresh_client.get("/api/v1/auth/csrf-token")
    assert second_response.status_code == 204
    second_token = fresh_client.cookies.get(settings.preauth_csrf_cookie_name)

    assert first_token == second_token
