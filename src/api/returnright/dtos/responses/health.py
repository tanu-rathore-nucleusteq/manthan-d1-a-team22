"""Health check result."""

from typing import Literal

from returnright.dtos.base import ResponseDTO

ComponentState = Literal["ok", "degraded", "down"]


class HealthResponse(ResponseDTO):
    status: ComponentState
    database: ComponentState
    gateway: ComponentState
