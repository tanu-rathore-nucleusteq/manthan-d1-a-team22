"""Liveness and readiness checks, including database and gateway reachability."""

import httpx
from fastapi import APIRouter, Response, status

from returnright.api.deps import AppSettings, DbSession
from returnright.db.session import ping_database
from returnright.dtos.responses.health import ComponentState, HealthResponse, LivenessResponse

router = APIRouter(prefix="/health", tags=["health"])


def check_gateway(base_url: str, timeout_seconds: float) -> ComponentState:
    try:
        reply = httpx.get(f"{base_url}/health", timeout=timeout_seconds)
    except httpx.HTTPError:
        return "down"
    return "ok" if reply.status_code == status.HTTP_200_OK else "degraded"


@router.get("", response_model=LivenessResponse, summary="Liveness: the API process is up")
def liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness: PostgreSQL and the payment gateway answer",
    responses={503: {"model": HealthResponse, "description": "The database is down"}},
)
def readiness(db: DbSession, settings: AppSettings, response: Response) -> HealthResponse:
    database: ComponentState = "ok" if ping_database(db) else "down"
    gateway = check_gateway(settings.gateway_url, min(settings.gateway_timeout_seconds, 1.0))

    if database == "down":
        overall: ComponentState = "down"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif gateway != "ok":
        overall = "degraded"  # returns still work; refunds wait for the gateway
    else:
        overall = "ok"
    return HealthResponse(status=overall, database=database, gateway=gateway)
