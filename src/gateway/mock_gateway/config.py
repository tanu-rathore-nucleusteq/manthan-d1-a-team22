"""Gateway settings from the environment (prefix GATEWAY_). Fault settings (latency, error rate,
outage) join here with the SRE story.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Processed idempotency keys live in gateway.payments (db/schema_v2.sql), so they survive a
    # gateway restart and a retry after a restart still never pays twice.
    database_url: str = "postgresql+psycopg://returnright:change-me@localhost:5434/returnright"


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()
