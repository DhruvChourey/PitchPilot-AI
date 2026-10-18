"""Password hashing -- a thin wrapper around argon2-cffi (the maintained
reference Argon2 binding; Argon2id is OWASP's current top recommendation,
ahead of bcrypt). No cryptographic primitives are implemented by hand here;
library defaults (time_cost=3, memory_cost=64 MiB, parallelism=4) already
match current OWASP guidance.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

_hasher = PasswordHasher()

# A precomputed dummy hash, verified against on every "user not found" login
# attempt so the response takes the same time as a real wrong-password
# check -- otherwise an attacker could distinguish "no such email" (fast)
# from "email exists, password wrong" (slow, since hashing takes time) via
# a timing side-channel, defeating the point of a generic error message.
_DUMMY_HASH = _hasher.hash("not-a-real-password-used-only-for-timing-parity")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def waste_time_like_a_password_check() -> None:
    """Call when a login's email lookup fails, before returning 401, so the
    response timing doesn't reveal whether the email exists."""
    try:
        _hasher.verify(_DUMMY_HASH, "irrelevant")
    except VerifyMismatchError:
        pass
