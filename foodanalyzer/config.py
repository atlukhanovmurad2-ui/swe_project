"""Typed application settings, read once from the environment / ``.env``.

Everything the SE layer needs to run is funnelled through :class:`Settings`.
Nothing else in the package should call :func:`os.getenv` directly (the
provided ``ai`` package still reads a handful of provider keys itself — that
is outside the contract and left untouched).
"""

from __future__ import annotations

import functools

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration.

    Values are resolved in this order: constructor kwargs, environment
    variables, ``.env`` file, then the defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- VLM / ingredient identification -------------------------------------
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # --- Nutrition provider ------------------------------------------------
    nutrition_provider: str = "usda"
    usda_api_key: str | None = None

    # --- Storage ---------------------------------------------------------
    # A PostgreSQL DSN (``postgresql://user:pass@host:5432/db``). When unset
    # or obviously a placeholder, the app falls back to an in-memory history
    # log so the demo, tests and a keyless container still run.
    database_url: str | None = None

    # --- Behaviour knobs -------------------------------------------------
    log_level: str = "INFO"
    nutrition_cache_ttl_seconds: int = Field(default=86_400, ge=0)
    max_image_size_mb: float = Field(default=5.0, gt=0)
    http_port: int = Field(default=8000, ge=1, le=65_535)
    max_concurrency: int = Field(default=10, ge=1, le=100)
    retry_max_attempts: int = Field(default=4, ge=1, le=10)
    retry_base_delay_seconds: float = Field(default=0.5, ge=0.0)
    retry_max_delay_seconds: float = Field(default=8.0, ge=0.0)
    upload_dir: str = "uploads"

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        v = v.strip().upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return v

    @property
    def max_image_size_bytes(self) -> int:
        return int(self.max_image_size_mb * 1024 * 1024)

    @property
    def has_real_database(self) -> bool:
        """True when ``database_url`` looks like a usable PostgreSQL DSN."""
        dsn = (self.database_url or "").strip()
        if not dsn or "://" not in dsn:
            return False
        scheme = dsn.split("://", 1)[0].split("+", 1)[0]
        return scheme in {"postgres", "postgresql"}

    def normalised_database_url(self) -> str | None:
        """Return a DSN asyncpg accepts, or ``None`` when there is no real DB."""
        if not self.has_real_database:
            return None
        dsn = self.database_url.strip()  # type: ignore[union-attr]
        # asyncpg does not understand SQLAlchemy-style ``+driver`` suffixes.
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests that patch the environment)."""
    get_settings.cache_clear()
