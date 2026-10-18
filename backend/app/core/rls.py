"""Sets the transaction-scoped Postgres GUC that the leads RLS policy reads.

Uses set_config(name, value, is_local=true) -- a normal SQL function call,
not the SET command -- so the value is passed as a regular bind parameter
(no string interpolation, no injection surface), and is_local=true gives
the same transaction-scoped behavior as SET LOCAL: it's cleared
automatically at COMMIT/ROLLBACK, which matters because the runtime role
is a single shared, pooled connection across all users' requests -- see
DECISIONS.md for why SET LOCAL (not SET) is required here, and for the
explicit limitation that this GUC is NOT a security boundary against SQL
injection or arbitrary SQL execution on the connection: any SQL running
as this role can set it to any value, including another user's UUID.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_rls_user_context(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(user_id)},
    )
