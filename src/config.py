from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    llm_provider: Literal["anthropic", "openai", "gemini"]
    llm_model: str

    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None

    nutrition_provider: Literal["usda"] = "usda"
    usda_api_key: SecretStr | None = None

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str

    nutrition_cache_ttl_seconds: int = Field(default=86400, gt=0)
    max_image_size_mb: int = Field(default=5, gt=0)
    http_port: int = Field(default=8000, ge=1, le=65535)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_llm_api_key(self) -> str:
        
        key_by_provider = {
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "gemini": self.google_api_key,
        }

        key = key_by_provider[self.llm_provider]

        if key is None:
            raise ValueError(
                f"Missing API key for LLM_PROVIDER={self.llm_provider!r}."
            )

        return key.get_secret_value()

    def get_usda_api_key(self) -> str:
        
        if self.usda_api_key is None:
            raise ValueError("Missing USDA_API_KEY.")

        return self.usda_api_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()