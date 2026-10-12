import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app


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


@pytest.fixture(scope="session")
def test_engine():
    url = _require_test_database_url()
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
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
