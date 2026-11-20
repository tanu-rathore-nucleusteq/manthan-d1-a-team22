"""Payment and fault-switch payloads."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refund_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["INR"] = "INR"


class PaymentResponse(BaseModel):
    transaction_id: str
    status: Literal["succeeded", "failed"]
    amount: Decimal
    replayed: bool = False


class FaultSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latency_ms: int = Field(default=0, ge=0, le=30_000)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    down: bool = False
