from enum import StrEnum
from functools import lru_cache
from os import getenv
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    local = "local"
    test = "test"
    production = "production"


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.local
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: CsvList = Field(default_factory=list)
    database_url: PostgresDsn
    db_pool_size: int = 5
    db_max_overflow: int = 0
    db_pool_recycle: int = 1800
    db_echo: bool = False
    db_disable_prepared_statements: bool = False
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "none"

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.production


@lru_cache
def get_settings() -> Settings:
    return Settings()
