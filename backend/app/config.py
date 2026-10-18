from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "pitchpilot-api"
    backend_cors_origins: str = "http://localhost:3000"

    # Optional so the app (and /health) can still start without a database
    # configured. DB-backed endpoints fail loudly and explicitly instead.
    database_url: str | None = None
    test_database_url: str | None = None
    # Non-owner, least-privilege test role (pitchpilot_test_app) -- used
    # by tests to actually exercise the RLS policy, as opposed to
    # test_database_url (pitchpilot_test_runner), which owns the tables
    # and therefore bypasses RLS the same way `postgres` does in
    # production. Only used by tests; the real app_database_url (the
    # production equivalent, pitchpilot_app) is a future addition, not
    # wired up this checkpoint since nothing is applied to production yet.
    test_app_database_url: str | None = None

    # Session cookie. session_cookie_secure defaults to True (production
    # posture); override to False only for local http:// dev, where a
    # Secure-flagged cookie wouldn't be sent at all.
    session_cookie_name: str = "session_id"
    session_cookie_secure: bool = True
    session_ttl_days: int = 14

    # CSRF double-submit cookie -- readable by JS (not HttpOnly), echoed
    # back as a header on mutating requests; see DECISIONS.md.
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
