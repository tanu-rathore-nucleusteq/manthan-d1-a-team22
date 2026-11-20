"""Domain errors raised by services, such as NotEligible, InvalidTransition, AlreadyRefunded and
ApprovalRequired. api/exception_handlers.py turns them into HTTP responses.
"""


class DomainError(Exception):
    """Base class. `code` is a stable machine-readable value; `message` is safe to show users."""

    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PaymentGatewayError(DomainError):
    """The payment gateway did not pay. The refund stays unpaid and can be retried with the same
    idempotency key."""

    code = "payment_gateway_error"


class GatewayUnavailableError(PaymentGatewayError):
    code = "gateway_unavailable"

    def __init__(self, attempts: int) -> None:
        super().__init__(
            f"The payment gateway did not answer after {attempts} attempts. The refund was not "
            "paid twice; retry it later."
        )
        self.attempts = attempts


class IdempotencyConflictError(PaymentGatewayError):
    code = "idempotency_conflict"

    def __init__(self) -> None:
        super().__init__("This refund's idempotency key was already used for a different payment.")


class OrderNotFoundError(DomainError):
    code = "order_not_found"

    def __init__(self) -> None:
        # Same message whether the number or the email is wrong, so it reveals nothing.
        super().__init__("We couldn't find an order with that order number and email.")
