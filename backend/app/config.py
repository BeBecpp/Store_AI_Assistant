"""Application configuration loaded from environment."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Store Assistant"
    debug: bool = False

    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:5500,http://localhost:8080",
        description="Comma-separated allowed origins",
    )

    store_provider: str = "mock"
    store_api_url: str = ""
    store_api_key: str = ""
    store_api_timeout: int = 10

    ollama_base_url: str = ""
    ollama_model: str = "llama3.2"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    max_message_length: int = 1000

    frontend_static_path: str | None = Field(
        default=None,
        description="Optional path to static widget files (e.g. Docker mount).",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
