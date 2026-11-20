"""Typed settings loaded from environment variables (pydantic-settings). See .env.example."""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"

    # PostgreSQL
    database_url: str = "postgresql+psycopg://returnright:change-me@localhost:5434/returnright"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: int = Field(default=10, ge=1)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60)
    db_connect_timeout_seconds: int = Field(default=5, ge=1)
    db_statement_timeout_ms: int = Field(default=15_000, ge=0)
    db_echo: bool = False

    # Auth
    jwt_secret: str = Field(default="change-me-to-a-long-random-string", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=60, ge=1)

    # Mock payment gateway
    gateway_url: str = "http://localhost:8001"
    gateway_timeout_seconds: float = Field(default=2.0, gt=0)
    gateway_max_retries: int = Field(default=2, ge=0)

    # Uploads and business thresholds
    upload_dir: str = "uploads"
    upload_max_mb: int = Field(default=5, ge=1)
    photos_per_item_max: int = Field(default=5, ge=1)
    finance_approval_threshold_inr: Decimal = Decimal("10000")
    warehouse_address: str = (
        "ReturnRight Returns Centre, Plot 12, Sector 3, Pithampur Industrial Area, "
        "Dhar, Madhya Pradesh 454775"
    )

    # Seed script: password given to the demo staff users
    demo_password: str = Field(default="change-me-demo", min_length=8)

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string, as written in .env files."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
