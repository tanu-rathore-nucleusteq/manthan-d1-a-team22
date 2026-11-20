"""Health check result."""

from typing import Literal

from returnright.dtos.base import ResponseDTO

ComponentState = Literal["ok", "degraded", "down"]


class LivenessResponse(ResponseDTO):
    status: Literal["ok"] = "ok"


class HealthResponse(ResponseDTO):
    status: ComponentState
    database: ComponentState
    gateway: ComponentState
