"""Direct-SQL RLS tests -- bypass the FastAPI app entirely and talk to
Postgres through the restricted pitchpilot_test_app role directly, to
prove the RLS policy itself enforces isolation independent of any
application code correctness. See app/core/rls.py and DECISIONS.md for
the explicit limitation: this GUC is not a defense against SQL injection
or arbitrary SQL execution on the connection -- these tests prove the
*accidental-omission* defense-in-depth property, not a defense against a
malicious actor with SQL execution capability on this role.
"""

import uuid

import pytest
from sqlalchemy import text


@pytest.fixture()
def rls_connection(test_app_engine):
    """A raw connection as pitchpilot_test_app, one transaction per test,
    rolled back at teardown -- independent of the ORM/ownership fixtures
    above, to keep these tests honestly at the SQL level."""
    connection = test_app_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


def _insert_user(connection, user_id: uuid.UUID) -> None:
    # leads.owner_id has a FK to users.id -- a real row must exist there
    # regardless of what the RLS context is set to.
    connection.execute(
        text("INSERT INTO users (id, email, hashed_password, is_active) VALUES (:id, :email, 'unused', true)"),
        {"id": str(user_id), "email": f"rls-test-{user_id}@example.com"},
    )


def _insert_lead_as_context_user(connection, owner_id: uuid.UUID) -> uuid.UUID:
    """Inserts a lead for owner_id, having already set the RLS context to
    owner_id -- the WITH CHECK clause requires this to succeed."""
    _insert_user(connection, owner_id)
    connection.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(owner_id)}
    )
    lead_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO leads (id, owner_id, company_name, status) "
            "VALUES (:id, :owner_id, :name, 'new')"
        ),
        {"id": str(lead_id), "owner_id": str(owner_id), "name": "RLS Direct Test Co"},
    )
    return lead_id


def test_rls_denies_access_with_wrong_user_context(rls_connection):
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    lead_id = _insert_lead_as_context_user(rls_connection, owner_a)
    _insert_user(rls_connection, owner_b)

    # Set context to B, then try to see A's lead.
    rls_connection.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(owner_b)}
    )
    result = rls_connection.execute(
        text("SELECT id FROM leads WHERE id = :id"), {"id": str(lead_id)}
    ).fetchall()

    assert result == []


def test_rls_allows_access_with_correct_user_context(rls_connection):
    owner_a = uuid.uuid4()
    lead_id = _insert_lead_as_context_user(rls_connection, owner_a)

    # Context is already owner_a from the insert helper; re-set explicitly
    # to keep the test's intent self-evident.
    rls_connection.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(owner_a)}
    )
    result = rls_connection.execute(
        text("SELECT id FROM leads WHERE id = :id"), {"id": str(lead_id)}
    ).fetchall()

    assert len(result) == 1


def test_rls_fails_closed_when_context_never_set(test_app_engine, test_engine):
    """Insert a committed row (as the admin/owner role, which bypasses RLS,
    so no context juggling is needed for the insert itself), then read it
    back via a brand-new pitchpilot_test_app connection/transaction that
    never calls set_config at all.

    Empirically confirmed (not assumed): on this Postgres/Supabase setup,
    current_setting('app.current_user_id', true) on a connection that has
    NEVER set it returns '' (empty string), not SQL NULL -- verified with
    a disposable brand-new engine with no prior fixture activity. Textbook
    Postgres docs describe NULL for an unset custom GUC; that is not what
    is observed here, so this test pins the actual behavior instead of an
    assumed one.

    The RLS policy casts this value with ::uuid, so '' fails the cast and
    the query raises a DataError -- i.e. the "forgot to call
    set_rls_user_context" bug fails LOUD (every leads query errors out)
    rather than failing open (never returns another user's rows) or
    failing silently empty. This is a real, materially different failure
    mode from "zero rows" and is recorded here precisely for that reason
    -- see HANDOFF.md's unresolved-risks section.
    """
    from sqlalchemy.exc import DataError

    owner_a = uuid.uuid4()
    with test_engine.begin() as admin_connection:
        _insert_user(admin_connection, owner_a)
        admin_connection.execute(
            text(
                "INSERT INTO leads (id, owner_id, company_name, status) "
                "VALUES (:id, :owner_id, :name, 'new')"
            ),
            {"id": str(uuid.uuid4()), "owner_id": str(owner_a), "name": "RLS Direct Test Co"},
        )

    fresh_connection = test_app_engine.connect()
    fresh_transaction = fresh_connection.begin()
    try:
        never_set = fresh_connection.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar()
        assert never_set == ""

        with pytest.raises(DataError):
            fresh_connection.execute(text("SELECT id FROM leads")).fetchall()
    finally:
        fresh_transaction.rollback()
        fresh_connection.close()
        with test_engine.begin() as admin_connection:
            admin_connection.execute(text("DELETE FROM leads WHERE owner_id = :id"), {"id": str(owner_a)})
            admin_connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(owner_a)})


def test_set_local_does_not_leak_across_transactions_on_same_connection(test_app_engine):
    """Proves the transaction-safety property directly: set the GUC, COMMIT,
    then check it's gone in a fresh transaction on the SAME physical
    connection -- the scenario that matters for a pooled, shared role
    where a connection may be reused by a different user's request."""
    owner_a = uuid.uuid4()
    connection = test_app_engine.connect()
    try:
        # First "request": set context, commit.
        trans1 = connection.begin()
        connection.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(owner_a)}
        )
        current = connection.execute(text("SELECT current_setting('app.current_user_id', true)")).scalar()
        assert current == str(owner_a)
        trans1.commit()

        # Second "request" on the SAME connection: a fresh transaction.
        trans2 = connection.begin()
        leaked = connection.execute(text("SELECT current_setting('app.current_user_id', true)")).scalar()
        trans2.rollback()

        assert leaked in (None, "")
    finally:
        connection.close()


def test_app_role_cannot_bypass_rls_or_own_leads_table(test_app_engine):
    with test_app_engine.connect() as connection:
        bypass = connection.execute(
            text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).scalar()
        is_owner = connection.execute(
            text(
                "SELECT pg_catalog.pg_get_userbyid(c.relowner) = current_user "
                "FROM pg_class c WHERE c.relname = 'leads' AND c.relnamespace = "
                "(SELECT oid FROM pg_namespace WHERE nspname = current_schema())"
            )
        ).scalar()

        assert bypass is False
        assert is_owner is False
