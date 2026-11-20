"""What the refund service sends to the payment gateway and what it gets back."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True, slots=True)
class GatewayPaymentRequest:
    refund_id: int
    amount: Decimal
    idempotency_key: str
    currency: str = "INR"


@dataclass(frozen=True, slots=True)
class GatewayPaymentResult:
    transaction_id: str
    status: Literal["succeeded", "failed"]
    replayed: bool
    latency_ms: float
