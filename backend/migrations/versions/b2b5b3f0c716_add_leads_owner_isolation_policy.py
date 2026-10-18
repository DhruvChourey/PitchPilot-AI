"""add leads owner isolation policy

Revision ID: b2b5b3f0c716
Revises: f8ee167d1484
Create Date: 2026-10-13 00:00:00.000000

AUTHORED FOR REVIEW ONLY -- NOT APPLIED. As with every other migration in
this project, migrations/env.py is hardcoded to DATABASE_URL (production)
and nothing has been run against it. This file exists so the production
RLS design can be reviewed before any future deployment decision, not
because it has been executed.

Preconditions this migration assumes and does NOT itself create:
  1. A `pitchpilot_app` Postgres role already exists, created out-of-band
     (not via this migration, and not via Alembic at all) the same way
     pitchpilot_test_app was created for tests: NOLOGIN-safe generated
     password, NOBYPASSRLS, no superuser/createrole, no access to schemas
     other than public, search_path pinned. Role creation embeds a
     generated password in raw SQL (CREATE/ALTER ROLE's PASSWORD clause
     doesn't support bind parameters) and must never be run through
     Alembic, which logs/echoes SQL and stores revision history in the
     database -- a password embedded in a migration body would leak into
     `alembic_version`-adjacent tooling output and migration file history
     permanently. Keep role creation in a standalone, one-time script
     whose output is never printed, exactly as this project's test role
     setup already does.
  2. The application's production database connection will need to
     switch from the current `postgres` (owner) role to `pitchpilot_app`
     for this policy to actually constrain anything -- until that
     connection switch happens, this migration (if ever applied) would be
     inert for the app itself, because the table owner bypasses RLS
     regardless of policies present. See 92142a5684c8's own comment for
     the identical point about ENABLE ROW LEVEL SECURITY.

What this migration does:
  - Grants the minimum DML privileges on public.leads to pitchpilot_app
    (no DDL, no ownership transfer, no BYPASSRLS).
  - Creates leads_owner_isolation, identical in shape to the policy
    verified against the pitchpilot_test / pitchpilot_test_app pair in
    Checkpoint 3's test suite (see backend/tests/test_rls.py).

What this migration deliberately does NOT do (unresolved risk -- see
HANDOFF.md): users and sessions are not RLS-protected by this design.
Only leads has an ownership column and policy. A future table that needs
per-user isolation needs its own column, grant and policy -- none of
this generalizes automatically.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b2b5b3f0c716"
down_revision: Union[str, Sequence[str], None] = "f8ee167d1484"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "pitchpilot_app"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.leads TO {APP_ROLE}")
    op.execute(
        f"CREATE POLICY leads_owner_isolation ON public.leads "
        "USING (owner_id = current_setting('app.current_user_id', true)::uuid) "
        "WITH CHECK (owner_id = current_setting('app.current_user_id', true)::uuid)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY IF EXISTS leads_owner_isolation ON public.leads")
    op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON public.leads FROM {APP_ROLE}")
