"""Domain errors raised by services, such as NotEligible, InvalidTransition, AlreadyRefunded and
ApprovalRequired. api/exception_handlers.py turns them into HTTP responses.
"""


class DomainError(Exception):
    """Base class. `code` is a stable machine-readable value; `message` is safe to show users."""

    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OrderNotFoundError(DomainError):
    code = "order_not_found"

    def __init__(self) -> None:
        # Same message whether the number or the email is wrong, so it reveals nothing.
        super().__init__("We couldn't find an order with that order number and email.")
