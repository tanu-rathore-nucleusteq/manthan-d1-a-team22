"""Settings from the environment: fault switches, the payment store and the admin token."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    latency_ms: int = Field(default=0, ge=0, le=30_000)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    down: bool = False
    # Empty: payments are kept in memory and forgotten on restart.
    database_url: str = ""
    # Empty: /admin/faults is open, which is fine on a laptop but not on a shared server.
    admin_token: str = ""


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
