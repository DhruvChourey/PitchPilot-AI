"""CSRF token generation and verification.

Two distinct, differently-keyed token flavors, not one token reused for
both purposes:

1. **Session-bound** (authenticated requests: lead mutations, logout).
   The token is `hex(HMAC(SECRET_KEY, "session:" + hashed_session_token))`
   -- deterministic, no stored nonce. Its security comes entirely from
   `hashed_session_token` only being knowable to someone who already holds
   the session's raw cookie (computing it requires the session row, which
   is looked up *by* that raw token) plus the server-side SECRET_KEY. This
   means the token is automatically invalidated whenever the session
   rotates (new login -> new session -> new hashed_token -> new token) --
   "rotation" falls out of the design for free, with no separate
   server-side CSRF-token table to manage.

2. **Pre-authentication** (login, register -- no session exists yet).
   The token is `nonce.hex(HMAC(SECRET_KEY, "preauth:" + nonce))`. Unlike
   the session-bound flavor this does need a stored (cookie-carried)
   nonce, since there's no other per-visitor secret to bind to yet; the
   signature still proves the cookie wasn't forged/tossed from a
   sibling/parent domain without knowing SECRET_KEY.

Both are intentionally *not* "plain cookie must equal header" (which is
what app/core/csrf.py used to be, and what app/dependencies.py's
verify_csrf comment originally described) -- that alone is sound only
because of SameSite=Lax; signing adds defense-in-depth against
cookie-tossing attacks on a shared parent/sibling domain, where SameSite
doesn't help since the attacker's subdomain *can* set (though not read)
a cookie on the shared parent domain.
"""

import hashlib
import hmac
import secrets

from app.config import settings

_SESSION_PREFIX = "session:"
_PREAUTH_PREFIX = "preauth:"


def _require_secret_key() -> str:
    if not settings.secret_key:
        raise RuntimeError(
            "SECRET_KEY is not configured. Set it in backend/.env "
            "(see .env.example) -- required to sign CSRF tokens."
        )
    return settings.secret_key


def _hmac_hex(message: str) -> str:
    key = _require_secret_key().encode("utf-8")
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_session_csrf_token(hashed_session_token: str) -> str:
    """The value to put in the CSRF cookie (and expect echoed back as the
    header) for an authenticated request bound to this session."""
    return _hmac_hex(_SESSION_PREFIX + hashed_session_token)


def verify_session_csrf_token(token: str, hashed_session_token: str) -> bool:
    expected = sign_session_csrf_token(hashed_session_token)
    return hmac.compare_digest(token, expected)


def generate_preauth_csrf_token() -> str:
    """The value to put in the pre-authentication CSRF cookie. Call this
    only when that cookie is missing from the incoming request -- it must
    not be regenerated on every response, or a legitimate multi-tab/
    multi-request flow could race against its own cookie being replaced."""
    nonce = secrets.token_urlsafe(32)
    signature = _hmac_hex(_PREAUTH_PREFIX + nonce)
    return f"{nonce}.{signature}"


def verify_preauth_csrf_token(token: str) -> bool:
    nonce, _, signature = token.partition(".")
    if not nonce or not signature:
        return False
    expected_signature = _hmac_hex(_PREAUTH_PREFIX + nonce)
    return hmac.compare_digest(signature, expected_signature)
