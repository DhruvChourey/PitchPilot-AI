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
    session_factory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
