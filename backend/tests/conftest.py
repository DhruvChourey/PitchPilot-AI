import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app
from app.models.user import User


TEST_SCHEMA = "pitchpilot_test"
assert TEST_SCHEMA != "public"  # guard against a copy-paste mistake
TEST_APP_ROLE = "pitchpilot_test_app"


def _require_test_database_url() -> str:
    if not settings.test_database_url:
        pytest.skip(
            "TEST_DATABASE_URL is not configured; set it in backend/.env to run "
            "database-backed tests. See README.md for setup instructions."
        )

    # The test fixtures below run Base.metadata.drop_all() at session end.
    # Refuse to run at all if TEST_DATABASE_URL resolves to the same
    # database as DATABASE_URL (dev/Supabase) -- a misconfigured .env must
    # never result in dropping real tables.
    if settings.database_url and settings.test_database_url == settings.database_url:
        pytest.exit(
            "TEST_DATABASE_URL is identical to DATABASE_URL. Refusing to run "
            "database tests: they call Base.metadata.drop_all() at teardown, "
            "which would destroy the development/Supabase schema. Point "
            "TEST_DATABASE_URL at a separate, disposable database.",
            returncode=1,
        )

    return settings.test_database_url


def _require_test_app_database_url() -> str:
    if not settings.test_app_database_url:
        pytest.skip(
            "TEST_APP_DATABASE_URL is not configured; the restricted "
            "pitchpilot_test_app role must exist for RLS-aware tests. "
            "See HANDOFF.md's Checkpoint 3 section for setup."
        )
    if settings.database_url and settings.test_app_database_url == settings.database_url:
        pytest.exit(
            "TEST_APP_DATABASE_URL is identical to DATABASE_URL -- refusing to run.",
            returncode=1,
        )
    return settings.test_app_database_url


@pytest.fixture(scope="session")
def test_engine():
    """Admin/owner connection (pitchpilot_test_runner) -- creates tables,
    grants the restricted app role access to them, and sets up the RLS
    policy on leads. Nothing in the actual request-handling path (see
    db_session below) uses this engine to run queries -- only schema
    setup."""
    url = _require_test_database_url()
    engine = create_engine(url, pool_pre_ping=True).execution_options(
        schema_translate_map={None: TEST_SCHEMA}
    )
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # Raw SQL bypasses schema_translate_map, so the schema must be
        # named explicitly here.
        conn.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {TEST_SCHEMA} "
                f"TO {TEST_APP_ROLE}"
            )
        )
        conn.execute(text(f"ALTER TABLE {TEST_SCHEMA}.leads ENABLE ROW LEVEL SECURITY"))
        conn.execute(
            text(
                f"CREATE POLICY leads_owner_isolation ON {TEST_SCHEMA}.leads "
                "USING (owner_id = current_setting('app.current_user_id', true)::uuid) "
                "WITH CHECK (owner_id = current_setting('app.current_user_id', true)::uuid)"
            )
        )

    yield engine
    # Scoped to TEST_SCHEMA via the same schema_translate_map -- only drops
    # tables declared in Base.metadata, never a bare DROP SCHEMA/CASCADE.
    # The RLS policy is dropped automatically along with the table.
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def test_app_engine(test_engine):
    """The restricted, non-owner pitchpilot_test_app connection -- what
    actually runs application queries in tests, mirroring how the real
    app will connect to production as pitchpilot_app (once that's set
    up; not done this checkpoint). Depends on test_engine purely for
    fixture ordering (schema/grants/policy must exist first)."""
    url = _require_test_app_database_url()
    engine = create_engine(url, pool_pre_ping=True).execution_options(
        schema_translate_map={None: TEST_SCHEMA}
    )
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_app_engine):
    connection = test_app_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _make_test_client(db_session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _register_and_login(test_client: TestClient, password: str = "test-password-1") -> str:
    """Registers a fresh user and logs in on this TestClient instance (its
    cookie jar then holds that user's session). Returns the email, in case
    a test wants it."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    register_response = test_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert register_response.status_code == 201, register_response.text
    login_response = test_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login_response.status_code == 200, login_response.text
    return email


@pytest.fixture()
def client(db_session):
    """A TestClient authenticated as a freshly registered user. All 21
    pre-ownership lead tests call this exactly as before -- they're now
    implicitly authenticated, no test body changes needed."""
    test_client = _make_test_client(db_session)
    with test_client:
        _register_and_login(test_client)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def second_client(db_session):
    """A second TestClient, same underlying DB transaction (db_session) so
    both users' data is visible within one test, but its own independent
    cookie jar -- authenticated as a different user than `client`. Use
    this specifically for cross-user isolation tests."""
    test_client = _make_test_client(db_session)
    with test_client:
        _register_and_login(test_client)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_client():
    """TestClient with a MagicMock standing in for the DB session, and
    get_current_user overridden to a fixed fake user.

    Never opens a network connection -- safe to use for any test where the
    expected behavior (a Pydantic validation 422) happens before the
    endpoint body would touch the database at all. Do not use this for
    anything that needs the database to actually respond realistically
    (e.g. a 404-on-missing-row lookup) -- that belongs in the real-Postgres
    suite instead, to avoid tests passing against mock behavior that drifts
    from what Postgres actually does.

    get_current_user is overridden (not left to hit a real cookie/session
    lookup) because FastAPI resolves dependencies -- including auth --
    before/alongside body validation, and a dependency's raised exception
    (401, unauthenticated) takes priority over the body's 422: confirmed
    empirically when these tests started failing with 401 instead of 422
    after leads.py gained the auth dependency, not assumed from reading
    the FastAPI source.
    """

    def override_get_db():
        yield MagicMock()

    def override_get_current_user():
        return User(id=uuid.uuid4(), email="mock@example.com", hashed_password="unused", is_active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def lead_payload():
    return {
        "company_name": f"Acme Corp {uuid.uuid4().hex[:8]}",
        "website": "https://acme.example.com",
        "industry": "Manufacturing",
        "contact_name": "Jane Doe",
        "contact_email": "jane@acme.example.com",
        "source": "manual",
        "notes": "Met at a trade show.",
    }
