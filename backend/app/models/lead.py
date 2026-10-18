import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, FetchedValue, ForeignKey, Index, String, Text, func
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
    __table_args__ = (Index("ix_leads_status", "status"), Index("ix_leads_owner_id", "owner_id"))
    # SQLAlchemy's "auto" eager_defaults (the library default) only applies
    # RETURNING automatically on INSERT. For UPDATE, fetching a server-side
    # onupdate value (updated_at, below) via RETURNING instead of a
    # separate post-commit SELECT requires eager_defaults=True explicitly
    # -- confirmed by reading sqlalchemy/orm/persistence.py's
    # _collect_update_commands, which gates it on
    # `mapper.base_mapper.eager_defaults is True`, not "auto". Without
    # this, updated_at is left "expired" after an UPDATE flush and the
    # next access issues a fresh SELECT in a new transaction -- see
    # DECISIONS.md for why that broke under the RLS GUC's transaction
    # scoping.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Set from the authenticated server-side user only (app/api/v1/leads.py
    # never reads this from client-supplied payload -- LeadCreate/LeadUpdate
    # don't even define the field, so there's nothing for a client to send).
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
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
        # server_onupdate=FetchedValue() tells SQLAlchemy's eager-defaults
        # machinery to RETURNING this column on UPDATE (not just INSERT),
        # the same way server_default alone already does for INSERT --
        # without it, the ORM leaves the attribute "expired" after an
        # UPDATE flush and silently issues a separate SELECT the next
        # time it's accessed. That SELECT runs in a new transaction,
        # which is exactly what broke update_lead/archive_lead under the
        # RLS GUC's transaction scoping -- see DECISIONS.md.
        server_onupdate=FetchedValue(),
        nullable=False,
    )
