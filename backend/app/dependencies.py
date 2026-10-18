from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rls import set_rls_user_context
from app.core.sessions import get_valid_session
from app.database import get_db
from app.models.session import UserSession
from app.models.user import User


def get_current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    """Resolves the session cookie to a UserSession row, or raises 401.
    Use this directly when the route needs the session itself (e.g.
    logout, to revoke it); use get_current_user for everything else."""
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session = get_valid_session(db, raw_token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return session


def get_current_user(
    session: UserSession = Depends(get_current_session), db: Session = Depends(get_db)
) -> User:
    """Resolves the current session to its User, or raises 401. Also sets
    the transaction-scoped RLS context (app.current_user_id) for this
    request's database session -- see app/core/rls.py for exactly what
    security property this does and doesn't provide."""
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    set_rls_user_context(db, user.id)
    return user


def verify_csrf(request: Request) -> None:
    """Apply to mutating, cookie-authenticated routes. Compares the
    readable CSRF cookie to the X-CSRF-Token header -- both must be
    present and equal."""
    cookie_value = request.cookies.get(settings.csrf_cookie_name)
    header_value = request.headers.get(settings.csrf_header_name)
    if not cookie_value or not header_value or cookie_value != header_value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")
