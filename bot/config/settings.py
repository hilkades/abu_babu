from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")

    postgres_dsn: str = Field(alias="POSTGRES_DSN")
    redis_dsn: str = Field(alias="REDIS_DSN")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")

    default_mode: str = Field(default="balanced", alias="DEFAULT_MODE")
    default_confirm_timeout_sec: int = Field(default=90, alias="DEFAULT_CONFIRM_TIMEOUT_SEC")
    default_whitelist_ttl_sec: int = Field(default=24 * 3600, alias="DEFAULT_WHITELIST_TTL_SEC")


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

