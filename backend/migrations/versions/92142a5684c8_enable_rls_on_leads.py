"""enable rls on leads

Revision ID: 92142a5684c8
Revises: 9fbd56eca921
Create Date: 2026-10-12 22:45:51.360732

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92142a5684c8'
down_revision: Union[str, Sequence[str], None] = '9fbd56eca921'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enables RLS with zero policies -- Postgres then denies all access by
    # default to every non-bypassing role (anon, authenticated, service_role
    # via the Supabase Data API). Table owners bypass RLS automatically
    # unless FORCE ROW LEVEL SECURITY is also set, which this intentionally
    # does not do: the application connects as `postgres`, the table's
    # owner, so this has no effect on FastAPI's own queries. Adds no
    # policies, changes no grants, touches no data.
    op.execute("ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE public.leads DISABLE ROW LEVEL SECURITY")
