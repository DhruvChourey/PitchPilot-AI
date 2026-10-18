from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.csrf import verify_preauth_csrf_token, verify_session_csrf_token
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


def _origin_from_referer(referer: str) -> str | None:
    parts = urlsplit(referer)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def _verify_trusted_origin(request: Request) -> None:
    """Validates Origin (falling back to Referer's origin) against the
    exact configured, allow-listed origins -- never a wildcard, never a
    suffix/prefix match, and never any X-Forwarded-* header (those are
    client-settable and not authenticated by anything at this layer; see
    DECISIONS.md on why this project doesn't trust them without a known
    proxy topology in front of it).

    Chosen policy for a request with neither header: reject. A real
    browser sending a cookie-carrying fetch/XHR/form submission always
    sends at least one of these; their total absence is itself a signal
    this isn't that, not an ordinary case to special-case around.
    """
    allowed_origins = set(settings.cors_origins_list)

    origin = request.headers.get("origin")
    if origin is not None:
        if origin not in allowed_origins:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")
        return

    referer = request.headers.get("referer")
    if referer is not None:
        referer_origin = _origin_from_referer(referer)
        if referer_origin is None or referer_origin not in allowed_origins:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")


def verify_csrf_authenticated(request: Request, session: UserSession = Depends(get_current_session)) -> None:
    """Apply to mutating, cookie-authenticated routes (lead mutations,
    logout). Validates the session-bound, signed CSRF token (see
    app/core/csrf.py) and the request's Origin/Referer. Depending on
    get_current_session (not get_current_user) is deliberate: CSRF
    verification shouldn't require a successful User lookup to run, and
    FastAPI caches this dependency's result for the request, so routes
    that also depend on get_current_user don't pay for it twice."""
    _verify_trusted_origin(request)

    cookie_value = request.cookies.get(settings.csrf_cookie_name)
    header_value = request.headers.get(settings.csrf_header_name)
    if (
        not cookie_value
        or not header_value
        or cookie_value != header_value
        or not verify_session_csrf_token(cookie_value, session.hashed_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")


def verify_csrf_preauth(request: Request) -> None:
    """Apply to login/register -- routes that run before any session
    exists. Validates the pre-authentication CSRF token (see
    app/core/csrf.py) issued by GET /api/v1/auth/csrf-token, plus
    Origin/Referer."""
    _verify_trusted_origin(request)

    cookie_value = request.cookies.get(settings.preauth_csrf_cookie_name)
    header_value = request.headers.get(settings.csrf_header_name)
    if (
        not cookie_value
        or not header_value
        or cookie_value != header_value
        or not verify_preauth_csrf_token(cookie_value)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")
