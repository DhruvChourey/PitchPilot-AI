"""Double-submit cookie CSRF protection. SameSite=Lax on the session cookie
is the primary defense (it already blocks the cookie from being sent on
cross-site fetch/XHR); this is defense-in-depth on top of that, standard
for SPA + cookie-session combinations. No server-side token storage needed
-- it's a stateless equality check between a readable cookie and a header
the frontend must echo back.
"""

import secrets


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
