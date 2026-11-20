"""Allowed ReturnStatus transitions and who may trigger each; any other transition raises
InvalidTransition (409). Requested → Approved happens in the create transaction once every
submitted item is confirmed eligible. Received → Rejected when every item is rejected at
inspection; Inspected → Rejected when finance rejects. Refunded and Rejected are final.
"""

from returnright.core.exceptions import InvalidTransitionError
from returnright.domain.enums import ReturnStatus

ALLOWED_TRANSITIONS: dict[ReturnStatus, frozenset[ReturnStatus]] = {
    ReturnStatus.REQUESTED: frozenset({ReturnStatus.APPROVED, ReturnStatus.REJECTED}),
    ReturnStatus.APPROVED: frozenset({ReturnStatus.IN_TRANSIT}),
    ReturnStatus.IN_TRANSIT: frozenset({ReturnStatus.RECEIVED}),
    ReturnStatus.RECEIVED: frozenset({ReturnStatus.INSPECTED, ReturnStatus.REJECTED}),
    ReturnStatus.INSPECTED: frozenset({ReturnStatus.REFUNDED, ReturnStatus.REJECTED}),
    ReturnStatus.REFUNDED: frozenset(),
    ReturnStatus.REJECTED: frozenset(),
}

FINAL_STATUSES = frozenset({ReturnStatus.REFUNDED, ReturnStatus.REJECTED})

STATUS_LABELS = {
    ReturnStatus.REQUESTED: "requested",
    ReturnStatus.APPROVED: "approved",
    ReturnStatus.IN_TRANSIT: "in transit",
    ReturnStatus.RECEIVED: "received",
    ReturnStatus.INSPECTED: "inspected",
    ReturnStatus.REFUNDED: "refunded",
    ReturnStatus.REJECTED: "rejected",
}


def can_move(current: ReturnStatus, target: ReturnStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_can_move(current: ReturnStatus, target: ReturnStatus) -> None:
    if not can_move(current, target):
        raise InvalidTransitionError(
            f"This return is {STATUS_LABELS[current]}, so it can't be marked "
            f"{STATUS_LABELS[target]}."
        )
