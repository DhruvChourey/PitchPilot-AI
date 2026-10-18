"""add owner id to leads

Revision ID: f8ee167d1484
Revises: 804518e9ee21
Create Date: 2026-10-13 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f8ee167d1484'
down_revision: Union[str, Sequence[str], None] = '804518e9ee21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    NOT NULL added directly (no nullable-then-backfill staging) because
    production public.leads was confirmed to have 0 rows immediately
    before this migration was authored. Re-confirm the row count again,
    freshly, before ever applying this -- do not trust this comment as
    still being true later.
    """
    op.add_column(
        "leads",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_leads_owner_id_users", "leads", "users", ["owner_id"], ["id"]
    )
    op.create_index("ix_leads_owner_id", "leads", ["owner_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_leads_owner_id", table_name="leads")
    op.drop_constraint("fk_leads_owner_id_users", "leads", type_="foreignkey")
    op.drop_column("leads", "owner_id")
