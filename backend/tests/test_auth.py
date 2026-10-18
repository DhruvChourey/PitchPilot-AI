"""Auth endpoint tests, using the same real-Postgres `client` fixture as
test_leads.py (see conftest.py) -- the new users/sessions tables are
created automatically by the existing test_engine fixture's
Base.metadata.create_all(), since importing app.main pulls in the auth
router, which imports the User/UserSession models.

httpx's TestClient persists cookies across requests made on the same
client instance, so a register -> login -> me -> logout flow works
naturally without any extra plumbing.
"""

import uuid


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def test_register_success(client):
    email = _unique_email()
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-1"})

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert body["is_active"] is True
    assert body["email_verified_at"] is None
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email(client):
    email = _unique_email()
    client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-1"})

    response = client.post("/api/v1/auth/register", json={"email": email, "password": "another-password-1"})

    assert response.status_code == 409


def test_register_password_too_short(client):
    response = client.post(
        "/api/v1/auth/register", json={"email": _unique_email(), "password": "short"}
    )

    assert response.status_code == 422


def test_login_success_sets_cookies(client):
    email = _unique_email()
    password = "correct-horse-1"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})

    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == email
    assert "session_id" in response.cookies
    assert "csrf_token" in response.cookies
    # The raw session token must only ever travel via the Set-Cookie
    # header, never in the JSON response body.
    raw_token = response.cookies["session_id"]
    assert raw_token not in response.text
    assert "password" not in body
    assert "hashed_password" not in body
    assert "session" not in body
    assert "token" not in body


def test_login_wrong_password(client):
    email = _unique_email()
    client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-1"})

    response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_email_same_generic_message(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "whatever-1"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_requires_valid_session(client):
    # `client` is pre-authenticated by the fixture (needed now that every
    # lead endpoint requires auth); clear its cookie here to test the
    # genuinely-unauthenticated case instead of adding a separate fixture.
    client.cookies.delete("session_id")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_returns_current_user_after_login(client):
    email = _unique_email()
    password = "correct-horse-1"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    client.post("/api/v1/auth/login", json={"email": email, "password": password})

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == email


def test_logout_revokes_session(client):
    # CSRF enforcement is deferred to its own checkpoint -- logout is
    # intentionally callable with just the session cookie for now, no
    # X-CSRF-Token header required yet.
    email = _unique_email()
    password = "correct-horse-1"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    client.post("/api/v1/auth/login", json={"email": email, "password": password})

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    # The now-revoked session must no longer authenticate.
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


def test_me_rejects_expired_session(client, db_session):
    import hashlib
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.models.session import UserSession
    from app.models.user import User

    email = _unique_email()
    user = User(email=email, hashed_password="irrelevant-for-this-test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    raw_token = secrets.token_urlsafe(32)
    expired_session = UserSession(
        user_id=user.id,
        hashed_token=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # already expired
    )
    db_session.add(expired_session)
    db_session.commit()

    client.cookies.set("session_id", raw_token)
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
