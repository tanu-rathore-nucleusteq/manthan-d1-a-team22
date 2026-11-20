"""PaymentGateway protocol: pay(GatewayPaymentRequest) -> GatewayPaymentResult."""

from typing import Protocol

from returnright.dtos.internal.payments import GatewayPaymentRequest, GatewayPaymentResult


class PaymentGateway(Protocol):
    def pay(self, request: GatewayPaymentRequest) -> GatewayPaymentResult:
        """Pay once for request.idempotency_key. Raises GatewayUnavailableError when every attempt
        fails, IdempotencyConflictError when the key was used for a different payment."""
        ...
