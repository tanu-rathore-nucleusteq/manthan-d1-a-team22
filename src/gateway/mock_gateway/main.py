"""FastAPI app: POST /payments (Idempotency-Key header required) and GET /health.
POST /admin/faults and /metrics join with the SRE story.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from mock_gateway.dtos import PaymentRequest, PaymentResponse
from mock_gateway.store import IdempotencyConflictError, PaymentStore, get_engine, get_store

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    if get_engine.cache_info().currsize:
        get_engine().dispose()


app = FastAPI(
    title="Mock payment gateway",
    version="0.1.0",
    summary="Pays refunds exactly once per Idempotency-Key.",
    lifespan=lifespan,
)


@app.post(
    "/payments",
    response_model=PaymentResponse,
    summary="Pay a refund, or replay the first answer for a key already paid",
    responses={409: {"description": "The key was already used for a different payment"}},
)
def create_payment(
    payload: PaymentRequest,
    idempotency_key: Annotated[
        str, Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=64)
    ],
    store: Annotated[PaymentStore, Depends(get_store)],
) -> PaymentResponse:
    try:
        payment, replayed = store.pay_once(idempotency_key, payload)
    except IdempotencyConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Idempotency-Key was already used for a different payment.",
        ) from None
    return PaymentResponse(
        transaction_id=payment.transaction_id,
        status="succeeded",
        amount=payment.amount,
        replayed=replayed,
    )


@app.get("/health", summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}
