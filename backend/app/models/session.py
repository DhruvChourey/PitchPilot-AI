import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Named UserSession, not Session, to avoid colliding with
# sqlalchemy.orm.Session, which several files already import under that
# exact name.


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # SHA-256 hex digest of the opaque session token, never the raw token --
    # same principle as password storage: a DB leak alone shouldn't yield a
    # usable session. The raw token only ever exists in the Set-Cookie
    # response and the browser's cookie jar.
    hashed_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # NULL = still active. Set on logout; the row is kept (not deleted) for
    # audit purposes, same pattern as archiving a lead rather than deleting it.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
