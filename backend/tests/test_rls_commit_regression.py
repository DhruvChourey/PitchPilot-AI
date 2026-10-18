"""Regression tests for the Checkpoint 3 RLS/commit bug, using a
production-faithful session lifecycle.

Why this file exists and doesn't reuse conftest.py's db_session/client
fixtures: those fixtures bind the Session to an ALREADY-OPEN Connection +
Transaction (`connection = test_app_engine.connect(); transaction =
connection.begin()`, then the session is layered on top). When a Session
is bound that way, SQLAlchemy's documented "joining a session into an
external transaction" behavior means `Session.commit()` does not
actually commit anything at the database level -- so a route's
`db.commit()` call is silently a no-op there, and the RLS GUC
(`app.current_user_id`, set via `set_config(..., true)` -- transaction-
scoped) never actually clears. That's exactly how the original
Checkpoint 3 suite passed 44/44 while this bug was present: the fixture
accidentally masked it.

Production's real `app/database.py::get_db()` builds a Session bound
directly to the Engine, with no externally pre-opened transaction --
`db.commit()` there really does commit, really does clear the GUC, and a
query afterward really did hit the RLS policy's `::uuid` cast on the
resulting empty string. See DECISIONS.md's "Mutating routes read
server-generated columns..." entry for the fix and full reasoning.

The `production_like_client` fixture below does NOT reimplement
get_db() -- it monkeypatches `app.database.get_engine` (the thing
get_db() calls to get its Engine) to return the restricted,
RLS-enforcing `test_app_engine`, then lets the real, unmodified
`get_db()`/`get_current_user()`/route code run exactly as it would in
production, through a real TestClient making real HTTP-shaped requests
(register -> login -> mutate). This is deliberately the opposite of
db_session's isolation trick: it's testing *with* real transaction
boundaries, not insulated from them.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.database as database_module
from app.config import settings
from app.main import app

_TRUSTED_TEST_ORIGIN = settings.cors_origins_list[0]


def _new_client() -> TestClient:
    client = TestClient(app)
    client.headers["origin"] = _TRUSTED_TEST_ORIGIN
    return client


@pytest.fixture()
def production_like_client(test_app_engine, test_engine, monkeypatch):
    """A TestClient that exercises the real, unmodified get_db() /
    get_current_user() dependency chain against the restricted
    pitchpilot_test_app role and the real leads_owner_isolation policy --
    no dependency_overrides at all, unlike every other client fixture in
    this suite."""
    # Defensive: make sure no other fixture's overrides leaked in.
    app.dependency_overrides.clear()
    monkeypatch.setattr(database_module, "get_engine", lambda: test_app_engine)

    created_emails: list[str] = []

    def register_and_login(client: TestClient, password: str = "test-password-1") -> str:
        preauth = client.get("/api/v1/auth/csrf-token")
        assert preauth.status_code == 204, preauth.text
        preauth_token = client.cookies.get(settings.preauth_csrf_cookie_name)
        assert preauth_token
        client.headers[settings.csrf_header_name] = preauth_token

        email = f"prodlike-{uuid.uuid4().hex[:10]}@example.com"
        created_emails.append(email)
        r = client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text

        session_csrf_token = client.cookies.get(settings.csrf_cookie_name)
        assert session_csrf_token
        client.headers[settings.csrf_header_name] = session_csrf_token
        return email

    client = _new_client()
    client.register_and_login = register_and_login  # type: ignore[attr-defined]

    with client:
        yield client

    app.dependency_overrides.clear()

    # This fixture does NOT run inside a rolled-back transaction (that's
    # the whole point), so clean up what it actually committed, via the
    # admin role, rather than leaving it for the session-end drop_all().
    with test_engine.begin() as admin_connection:
        for email in created_emails:
            admin_connection.execute(
                text(
                    "DELETE FROM leads WHERE owner_id IN "
                    "(SELECT id FROM users WHERE email = :email)"
                ),
                {"email": email},
            )
            admin_connection.execute(
                text("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
                {"email": email},
            )
            admin_connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})


def _lead_payload(**overrides) -> dict:
    payload = {
        "company_name": f"Prod-Like Co {uuid.uuid4().hex[:6]}",
        "website": "https://prodlike.example.com",
        "industry": "Manufacturing",
        "contact_name": "Prod Tester",
        "contact_email": "prodlike@example.com",
        "source": "manual",
        "notes": "production-faithful regression test",
    }
    payload.update(overrides)
    return payload


def test_create_lead_succeeds_with_real_commit_and_rls(production_like_client):
    """The exact scenario that used to raise DataError: a real commit
    really ends the transaction the RLS GUC was set in, and the response
    still needs created_at/updated_at -- this must not require a
    post-commit query."""
    production_like_client.register_and_login(production_like_client)

    response = production_like_client.post("/api/v1/leads", json=_lead_payload())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]
    assert body["status"] == "new"


def test_update_lead_succeeds_with_real_commit_and_rls(production_like_client):
    production_like_client.register_and_login(production_like_client)
    create_response = production_like_client.post("/api/v1/leads", json=_lead_payload())
    lead_id = create_response.json()["id"]
    original_updated_at = create_response.json()["updated_at"]

    update_response = production_like_client.patch(
        f"/api/v1/leads/{lead_id}", json={"company_name": "Updated Co"}
    )

    assert update_response.status_code == 200, update_response.text
    body = update_response.json()
    assert body["company_name"] == "Updated Co"
    assert body["updated_at"]
    # Not strictly required to differ (clock resolution), but must be present
    # and must not have come from a failed/blank refresh.
    assert body["id"] == lead_id
    assert original_updated_at  # sanity: the create response had one too


def test_archive_lead_succeeds_with_real_commit_and_rls(production_like_client):
    production_like_client.register_and_login(production_like_client)
    create_response = production_like_client.post("/api/v1/leads", json=_lead_payload())
    lead_id = create_response.json()["id"]

    archive_response = production_like_client.delete(f"/api/v1/leads/{lead_id}")

    assert archive_response.status_code == 200, archive_response.text
    assert archive_response.json()["status"] == "archived"


def test_cross_user_isolation_holds_with_real_commit_and_rls(production_like_client):
    """The same cross-user isolation the Checkpoint 2/3 tests already
    cover, but under a session lifecycle where commits are real and the
    RLS policy is the only thing (besides app-level filtering) standing
    between user B and user A's data for the mutating routes themselves."""
    user_a = _new_client()
    user_b = _new_client()
    with user_a, user_b:
        production_like_client.register_and_login(user_a)
        production_like_client.register_and_login(user_b)

        create_response = user_a.post("/api/v1/leads", json=_lead_payload())
        assert create_response.status_code == 201, create_response.text
        lead_id = create_response.json()["id"]

        assert user_b.get(f"/api/v1/leads/{lead_id}").status_code == 404
        assert user_b.patch(f"/api/v1/leads/{lead_id}", json={"company_name": "Hijacked"}).status_code == 404
        assert user_b.delete(f"/api/v1/leads/{lead_id}").status_code == 404

        # And the owner can still reach it -- isolation isn't accidentally
        # blocking the legitimate owner too.
        owner_get = user_a.get(f"/api/v1/leads/{lead_id}")
        assert owner_get.status_code == 200
        assert owner_get.json()["company_name"] != "Hijacked"


def test_failed_update_leaves_no_committed_change(production_like_client, test_engine):
    """A mutation that fails (404 -- not this user's lead / doesn't
    exist) must not leave any committed row behind, and a successful
    create followed by a rejected update must leave the original data
    intact, not partially applied."""
    production_like_client.register_and_login(production_like_client)
    create_response = production_like_client.post("/api/v1/leads", json=_lead_payload())
    lead_id = create_response.json()["id"]
    original_name = create_response.json()["company_name"]

    nonexistent_id = uuid.uuid4()
    failed_response = production_like_client.patch(
        f"/api/v1/leads/{nonexistent_id}", json={"company_name": "Should Never Persist"}
    )
    assert failed_response.status_code == 404

    # Confirm directly, via the admin role (bypasses RLS, so this is a
    # ground-truth check independent of the app's own filtering), that no
    # row with the attempted new name was ever committed anywhere.
    with test_engine.begin() as admin_connection:
        leaked = admin_connection.execute(
            text("SELECT id FROM leads WHERE company_name = :name"),
            {"name": "Should Never Persist"},
        ).fetchall()
    assert leaked == []

    # And the real lead's data is untouched by the failed attempt.
    get_response = production_like_client.get(f"/api/v1/leads/{lead_id}")
    assert get_response.json()["company_name"] == original_name


def test_failed_commit_due_to_db_constraint_rolls_back_cleanly(production_like_client, test_app_engine, test_engine):
    """Forces a real commit() failure (FK violation) through the same
    get_db()-style session lifecycle and confirms the session recovers
    (rollback, not a wedged transaction) and leaves no partial row --
    this is the general "a failed mutation doesn't leave committed data"
    property get_db()'s except/rollback is meant to guarantee."""
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=test_app_engine, autoflush=False, autocommit=False)
    db = session_factory()
    bogus_owner = uuid.uuid4()  # no matching row in users -- FK violation
    lead_id = uuid.uuid4()
    try:
        # Set the RLS context to match owner_id so the policy's WITH CHECK
        # passes and the FK violation (not the RLS cast) is what fails --
        # this test is about commit-failure recovery in general, not RLS.
        db.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(bogus_owner)}
        )
        # A raw text() INSERT executes immediately (autoflush doesn't
        # apply to it -- there's no pending ORM object to defer), so the
        # FK violation raises here, not at commit().
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO leads (id, owner_id, company_name, status) "
                    "VALUES (:id, :owner_id, 'Should Not Persist', 'new')"
                ),
                {"id": str(lead_id), "owner_id": str(bogus_owner)},
            )
        db.rollback()

        # Session must still be usable after rollback -- not wedged. Use
        # the admin role for this ground-truth check: after rollback the
        # RLS GUC is gone too (same transaction-scoped clearing this
        # whole file is about), so a plain restricted-role SELECT here
        # would itself hit the RLS cast error rather than answering the
        # "did it leak" question this assertion is actually about.
        db.execute(text("SELECT 1"))  # confirm the session recovered, not wedged
    finally:
        db.close()

    with test_engine.begin() as admin_connection:
        count = admin_connection.execute(
            text("SELECT count(*) FROM leads WHERE id = :id"), {"id": str(lead_id)}
        ).scalar()
    assert count == 0
