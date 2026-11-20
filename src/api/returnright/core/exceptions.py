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


STAFF_NOT_FOUND = "We couldn't find a return with that code. Check the label and try again."


class ReturnNotFoundError(DomainError):
    code = "return_not_found"

    def __init__(
        self, message: str = "We couldn't find a return with that code and email."
    ) -> None:
        # For customers, the same message whether the code or the email is wrong.
        super().__init__(message)


class RefundNotFoundError(DomainError):
    code = "refund_not_found"

    def __init__(self) -> None:
        super().__init__("We couldn't find that refund.")


class InvalidCredentialsError(DomainError):
    code = "invalid_credentials"

    def __init__(self) -> None:
        super().__init__("Wrong username or password.")


class InvalidDateRangeError(DomainError):
    code = "invalid_date_range"

    def __init__(self) -> None:
        super().__init__("The start date must be on or before the end date.")


class InvalidReturnRequestError(DomainError):
    """The request names items that are not in the order, repeats one, or asks for too many."""

    code = "invalid_return_request"


class ItemNotEligibleError(DomainError):
    code = "item_not_eligible"


class DuplicateReturnError(DomainError):
    code = "duplicate_return"

    def __init__(self) -> None:
        super().__init__(
            "One of these items is already in an open return. Check your existing return "
            "instead of creating a new one."
        )


class InvalidTransitionError(DomainError):
    code = "invalid_transition"


class AlreadyReceivedError(InvalidTransitionError):
    code = "already_received"

    def __init__(self) -> None:
        super().__init__("Already received: this parcel was scanned before. Nothing changed.")


class InspectionMismatchError(DomainError):
    """The inspection doesn't cover every item of the return exactly once."""

    code = "inspection_mismatch"


class ConcurrentUpdateError(DomainError):
    code = "concurrent_update"

    def __init__(self) -> None:
        super().__init__("Someone else changed this return at the same time. Reload and try again.")


class NoPendingApprovalError(DomainError):
    code = "no_pending_approval"

    def __init__(self) -> None:
        super().__init__("This return isn't waiting for a finance decision.")


class AlreadyDecidedError(DomainError):
    code = "already_decided"

    def __init__(self) -> None:
        super().__init__("Finance has already decided on this return.")


class LabelUnavailableError(DomainError):
    code = "label_unavailable"

    def __init__(self) -> None:
        super().__init__("This return was rejected, so it has no shipping label.")


class RefundNotPayableError(DomainError):
    code = "refund_not_payable"


class PhotoRejectedError(DomainError):
    """Wrong file type, empty file or too many photos for one item."""

    code = "photo_rejected"


class PhotoTooLargeError(DomainError):
    code = "photo_too_large"

    def __init__(self, max_mb: int) -> None:
        super().__init__(f"The photo is larger than {max_mb} MB. Choose a smaller one.")
