import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeadStatus(str, enum.Enum):
    NEW = "new"
    RESEARCHING = "researching"
    RESEARCHED = "researched"
    PITCH_READY = "pitch_ready"
    ARCHIVED = "archived"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[LeadStatus] = mapped_column(
        Enum(
            LeadStatus,
            name="lead_status",
            native_enum=True,
            # SQLAlchemy's Enum defaults to using each Python member's .name
            # ("NEW", "RESEARCHING", ...) as the database-side value. The
            # actual Postgres enum (created by the Alembic migration, with
            # explicit lowercase literals) only has the .value strings
            # ("new", "researching", ...). Without values_callable, any
            # INSERT/UPDATE sends the uppercase .name and Postgres rejects
            # it with "invalid input value for enum lead_status" -- this
            # mismatch was latent and undetected until the first real
            # create_all()/insert against a live database surfaced it.
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=LeadStatus.NEW,
        server_default=LeadStatus.NEW.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
