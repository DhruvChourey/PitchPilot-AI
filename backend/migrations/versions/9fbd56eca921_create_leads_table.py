"""create leads table

Revision ID: 9fbd56eca921
Revises:
Create Date: 2026-10-12 12:49:08.433040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9fbd56eca921'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEAD_STATUS_VALUES = ("new", "researching", "researched", "pitch_ready", "archived")
LEAD_STATUS_ENUM = postgresql.ENUM(*LEAD_STATUS_VALUES, name="lead_status")


def upgrade() -> None:
    """Upgrade schema."""
    LEAD_STATUS_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            LEAD_STATUS_ENUM,
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_leads_status", "leads", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_table("leads")
    LEAD_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
