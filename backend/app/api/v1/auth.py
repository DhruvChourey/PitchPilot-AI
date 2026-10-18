from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.csrf import generate_preauth_csrf_token, sign_session_csrf_token, verify_preauth_csrf_token
from app.core.rate_limit import enforce_login_rate_limit, enforce_register_rate_limit
from app.core.security import hash_password, verify_password, waste_time_like_a_password_check
from app.core.sessions import create_session, revoke_session
from app.database import get_db
from app.dependencies import get_current_session, get_current_user, verify_csrf_authenticated, verify_csrf_preauth
from app.models.session import UserSession
from app.models.user import User
from app.schemas.user import UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, raw_session_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


def _set_session_csrf_cookie(response: Response, hashed_session_token: str) -> None:
    # Deliberately NOT httponly -- the frontend must be able to read this
    # and echo it back as a header (double-submit CSRF pattern). The
    # value is derived (see app/core/csrf.py), not stored -- "rotation"
    # just means a new session produces a new derived value here.
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=sign_session_csrf_token(hashed_session_token),
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


@router.get("/csrf-token", status_code=status.HTTP_204_NO_CONTENT)
def issue_preauth_csrf_token(request: Request, response: Response) -> None:
    """Issues the pre-authentication CSRF cookie, but only if the request
    doesn't already carry a valid one -- never regenerates it on every
    call. The frontend calls this once before rendering the login/
    register form; login/register themselves don't issue this cookie, so
    a forged cross-site POST straight to /login can't bootstrap its own
    valid pair."""
    existing = request.cookies.get(settings.preauth_csrf_cookie_name)
    if existing and verify_preauth_csrf_token(existing):
        return None

    response.set_cookie(
        key=settings.preauth_csrf_cookie_name,
        value=generate_preauth_csrf_token(),
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=60 * 60,  # short-lived: only needs to survive one form fill-in
        path="/",
    )
    return None


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_preauth)],
)
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)) -> User:
    enforce_register_rate_limit(request, payload.email)

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        # Unlike login, registration intentionally reveals "already
        # registered" -- the caller is actively trying to create an
        # account, not probing for valid emails, so this isn't the same
        # enumeration concern login has.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=UserRead, dependencies=[Depends(verify_csrf_preauth)])
def login(request: Request, payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> User:
    enforce_login_rate_limit(request, payload.email)

    user = db.query(User).filter(User.email == payload.email).first()

    if user is None:
        waste_time_like_a_password_check()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    session, raw_token = create_session(db, user.id)
    _set_session_cookie(response, raw_token)
    _set_session_csrf_cookie(response, session.hashed_token)
    # The pre-auth cookie's job is done once a session exists; drop it so
    # it isn't mistaken for the (differently-signed) session-bound token.
    response.delete_cookie(settings.preauth_csrf_cookie_name, path="/")
    return user


@router.post("/logout", dependencies=[Depends(verify_csrf_authenticated)])
def logout(
    response: Response,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    revoke_session(db, session)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return {"status": "logged out"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
