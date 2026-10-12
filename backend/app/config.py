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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
