"""Opaque server-side session tokens. Only a SHA-256 hash of each token is
ever stored -- the raw token exists only in the Set-Cookie response and the
browser's cookie jar, never in the database or logs.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.models.session import UserSession


def _generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_session(db: DbSession, user_id: uuid.UUID) -> tuple[UserSession, str]:
    """Returns (the new UserSession row, the raw token -- give this to the
    caller for the cookie, never persist it)."""
    raw_token = _generate_raw_token()
    session = UserSession(
        user_id=user_id,
        hashed_token=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def get_valid_session(db: DbSession, raw_token: str) -> UserSession | None:
    hashed = _hash_token(raw_token)
    session = db.query(UserSession).filter(UserSession.hashed_token == hashed).first()
    if session is None:
        return None
    if session.revoked_at is not None:
        return None
    # expires_at is stored timezone-aware (DateTime(timezone=True)); compare
    # against an aware "now" to avoid naive/aware comparison errors.
    if session.expires_at < datetime.now(timezone.utc):
        return None
    return session


def revoke_session(db: DbSession, session: UserSession) -> None:
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
