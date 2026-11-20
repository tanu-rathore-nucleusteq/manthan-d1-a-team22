"""PaymentGateway protocol: pay(GatewayPaymentRequest) -> GatewayPaymentResult."""

from typing import Protocol

from returnright.dtos.internal.payments import GatewayPaymentRequest, GatewayPaymentResult


class GatewayUnavailableError(Exception):
    """No usable answer after every retry, so the payment's outcome is unknown. Retrying later
    with the same idempotency key is always safe."""


class PaymentGateway(Protocol):
    def pay(self, request: GatewayPaymentRequest) -> GatewayPaymentResult:
        """Pay once per request.idempotency_key; raise GatewayUnavailableError on failure."""
        ...
