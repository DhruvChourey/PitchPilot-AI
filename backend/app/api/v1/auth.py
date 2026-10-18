from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.csrf import generate_csrf_token
from app.core.security import hash_password, verify_password, waste_time_like_a_password_check
from app.core.sessions import create_session, revoke_session
from app.database import get_db
from app.dependencies import get_current_session, get_current_user
from app.models.session import UserSession
from app.models.user import User
from app.schemas.user import UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, raw_session_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )
    # Deliberately NOT httponly -- the frontend must be able to read this
    # and echo it back as a header (double-submit CSRF pattern).
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=generate_csrf_token(),
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
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


@router.post("/login", response_model=UserRead)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.email == payload.email).first()

    if user is None:
        waste_time_like_a_password_check()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    _, raw_token = create_session(db, user.id)
    _set_auth_cookies(response, raw_token)
    return user


@router.post("/logout")
def logout(
    response: Response,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
    # CSRF enforcement is deliberately deferred to its own checkpoint (not
    # in scope here) -- the CSRF cookie is still issued at login (see
    # _set_auth_cookies) so the frontend has it ready, but nothing checks
    # it yet.
) -> dict[str, str]:
    revoke_session(db, session)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return {"status": "logged out"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
