from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in backend/.env "
            "(see .env.example) to use database-backed endpoints."
        )
    return create_engine(settings.database_url, pool_pre_ping=True)


def get_db() -> Generator[Session, None, None]:
    # expire_on_commit=False: see DECISIONS.md's "Mutating routes read
    # server-generated columns from the same transaction that writes them"
    # entry. In short: SQLAlchemy's default (True) would make any
    # attribute access on a just-committed ORM object (e.g. FastAPI/
    # Pydantic serializing the response) trigger an implicit SELECT in a
    # brand-new transaction -- which is exactly the bug this fixes, since
    # the RLS GUC is transaction-scoped and has already cleared by then.
    session_factory = sessionmaker(
        bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False
    )
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
