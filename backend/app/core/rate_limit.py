"""In-memory, sliding-window rate limiting for login/register.

Deliberately hand-rolled rather than adding a new dependency (slowapi/
limits): the existing stack has nothing like this, the logic needed is
small, and a home-grown limiter is trivial to make deterministically
testable (inject a fake clock) without real sleeps.

**Known production limitation, not silently glossed over**: this state
is process-local. Running more than one backend instance (e.g. behind a
load balancer) means each instance enforces its own independent counters
-- an attacker spread across instances effectively gets
`limit * instance_count`. A shared backend (e.g. Redis) is required
before horizontal scaling; not implemented here since no such
infrastructure exists yet for this project. See DECISIONS.md.

Keying: per-IP (`request.client.host`, as Starlette/uvicorn itself sees
the peer -- never an X-Forwarded-* header, which is attacker-settable
unless a specific trusted proxy is configured, which isn't the case
here) and per-normalized-email, independently. Email is never stored or
logged in cleartext as a limiter key -- it's hashed first -- so that if
this in-memory state were ever dumped for debugging, raw submitted
emails wouldn't be sitting in it.

Both are throttles (429 + Retry-After), never an account-lockout flag
persisted anywhere -- that would let an attacker lock a *victim* out by
deliberately tripping their per-email limit.
"""

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: float


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = retry_after_seconds


class RateLimiter:
    """One independent bucket per key. `clock` is a zero-arg callable
    returning a monotonically increasing float; tests monkeypatch this
    attribute directly to control time without sleeping."""

    def __init__(self) -> None:
        self.clock = time.monotonic
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, rule: RateLimitRule) -> None:
        now = self.clock()
        bucket = self._hits[key]
        cutoff = now - rule.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= rule.max_requests:
            retry_after = bucket[0] + rule.window_seconds - now
            raise RateLimitExceeded(retry_after_seconds=max(retry_after, 0.0))
        bucket.append(now)

    def reset(self) -> None:
        """Test-only: clear all buckets so one test's requests can't
        exhaust a limit another test then trips on."""
        self._hits.clear()


def _hash_email(email: str) -> str:
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


login_ip_limiter = RateLimiter()
login_email_limiter = RateLimiter()
register_ip_limiter = RateLimiter()
register_email_limiter = RateLimiter()

LOGIN_IP_RULE = RateLimitRule(max_requests=10, window_seconds=60)
LOGIN_EMAIL_RULE = RateLimitRule(max_requests=5, window_seconds=300)
REGISTER_IP_RULE = RateLimitRule(max_requests=5, window_seconds=60)
REGISTER_EMAIL_RULE = RateLimitRule(max_requests=3, window_seconds=300)


def _enforce(limiter: RateLimiter, key: str, rule: RateLimitRule, detail: str) -> None:
    try:
        limiter.check(key, rule)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(int(exc.retry_after_seconds) + 1)},
        ) from None


def enforce_login_rate_limit(request: Request, email: str) -> None:
    ip = _client_ip(request)
    _enforce(login_ip_limiter, ip, LOGIN_IP_RULE, "Too many login attempts from this address, try again later.")
    _enforce(
        login_email_limiter,
        _hash_email(email),
        LOGIN_EMAIL_RULE,
        "Too many login attempts for this account, try again later.",
    )


def enforce_register_rate_limit(request: Request, email: str) -> None:
    ip = _client_ip(request)
    _enforce(
        register_ip_limiter, ip, REGISTER_IP_RULE, "Too many registration attempts from this address, try again later."
    )
    _enforce(
        register_email_limiter,
        _hash_email(email),
        REGISTER_EMAIL_RULE,
        "Too many registration attempts for this email, try again later.",
    )


def reset_all_rate_limits() -> None:
    """Test-only hook -- see tests/conftest.py's autouse fixture."""
    for limiter in (login_ip_limiter, login_email_limiter, register_ip_limiter, register_email_limiter):
        limiter.reset()
        limiter.clock = time.monotonic
