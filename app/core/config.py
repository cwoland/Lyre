from enum import StrEnum
from functools import lru_cache
from os import getenv
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    local = "local"
    test = "test"
    production = "production"

def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value

CsvList = Annotated[list[str], BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment.local
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: CsvList = Field(default_factory=list)

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.production


@lru_cache
def get_settings() -> Settings:
    return Settings()
