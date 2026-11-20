"""FastAPI app: POST /payments (Idempotency-Key header required), GET /health, and GET and
POST /admin/faults to change the fault switches at runtime.
"""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status

from mock_gateway.config import GatewaySettings, get_settings
from mock_gateway.dtos import FaultSettings, PaymentRequest, PaymentResponse
from mock_gateway.faults import FaultSwitches
from mock_gateway.store import KeyReusedError, MemoryStore, PaymentStore, PostgresStore

router = APIRouter()


def get_store(request: Request) -> PaymentStore:
    return request.app.state.store


def get_faults(request: Request) -> FaultSwitches:
    return request.app.state.faults


def require_admin(
    request: Request,
    token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    expected = request.app.state.admin_token
    if expected and not secrets.compare_digest(token or "", expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token needed")


Store = Annotated[PaymentStore, Depends(get_store)]
Faults = Annotated[FaultSwitches, Depends(get_faults)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)]


@router.post(
    "/payments",
    response_model=PaymentResponse,
    summary="Pay a refund once per idempotency key",
    responses={
        409: {"description": "The key was already used for a different payment"},
        502: {"description": "Simulated bank error; nothing was paid, retry with the same key"},
        503: {"description": "Simulated outage; nothing was paid"},
    },
)
def pay(
    payload: PaymentRequest, idempotency_key: IdempotencyKey, store: Store, faults: Faults
) -> PaymentResponse:
    if faults.outage():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The payment provider is offline")
    if faults.transient_error():
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The bank did not answer and nothing was paid. Retry with the same key.",
        )
    try:
        payment, replayed = store.pay_once(
            idempotency_key, payload.refund_id, payload.amount, payload.currency
        )
    except KeyReusedError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This key was already used for a different payment."
        ) from error
    # The delay comes after the money moves: a client that times out here has been paid, and its
    # retry with the same key gets this answer replayed.
    faults.delay()
    return PaymentResponse(
        transaction_id=payment.transaction_id,
        status="succeeded",
        amount=payment.amount,
        replayed=replayed,
    )


@router.get("/health", summary="Liveness")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/admin/faults", response_model=FaultSettings, summary="Current fault switches")
def read_faults(faults: Faults) -> FaultSettings:
    return faults.current


@router.post(
    "/admin/faults",
    response_model=FaultSettings,
    summary="Change the fault switches: latency, error rate, outage",
    dependencies=[Depends(require_admin)],
)
def change_faults(settings: FaultSettings, faults: Faults) -> FaultSettings:
    faults.update(settings)
    return faults.current


def create_app(
    settings: GatewaySettings | None = None, store: PaymentStore | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Mock payment gateway",
        version="1.0.0",
        summary="Pays refunds once per idempotency key, with switches to make it slow or broken.",
    )
    if store is None:
        store = PostgresStore(settings.database_url) if settings.database_url else MemoryStore()
    app.state.store = store
    app.state.faults = FaultSwitches(
        FaultSettings(
            latency_ms=settings.latency_ms, error_rate=settings.error_rate, down=settings.down
        )
    )
    app.state.admin_token = settings.admin_token
    app.include_router(router)
    return app


app = create_app()
