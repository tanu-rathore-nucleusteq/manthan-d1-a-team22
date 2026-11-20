"""Warehouse work: the queue, finding a return by its QR code, receiving the parcel (a second
scan changes nothing) and inspecting every item, which creates the refunds and pays them at once
unless the return total needs finance approval.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from returnright.core.config import Settings
from returnright.core.exceptions import (
    AlreadyReceivedError,
    ConcurrentUpdateError,
    InspectionMismatchError,
    InvalidTransitionError,
    ReturnNotFoundError,
)
from returnright.domain.enums import RefundStatus, ReturnStatus
from returnright.domain.refund_policy import (
    needs_finance_approval,
    refund_amount,
    refund_percent,
    refund_total,
)
from returnright.domain.state_machine import ensure_can_move
from returnright.dtos.internal.audit import Actor
from returnright.dtos.internal.auth import CurrentUser
from returnright.dtos.requests.warehouse import InspectionRequest
from returnright.dtos.responses.common import PageResponse
from returnright.dtos.responses.returns import ReturnDetailResponse, ReturnSummaryResponse
from returnright.dtos.responses.warehouse import InspectionResultResponse
from returnright.mappers.return_mapper import to_inspection_result, to_return_detail, to_summary
from returnright.models.refund import Refund
from returnright.models.return_request import Inspection, ReturnRequest
from returnright.repositories.audit_repository import AuditRepository
from returnright.repositories.return_repository import ReturnRepository
from returnright.services.audit_service import AuditTrail, ReturnTransitions
from returnright.services.refund_service import RefundService
from returnright.utils.clock import Clock

AFTER_RECEIPT = {ReturnStatus.RECEIVED, ReturnStatus.INSPECTED, ReturnStatus.REFUNDED}


class InspectionService:
    def __init__(
        self, session: Session, settings: Settings, clock: Clock, refunds: RefundService
    ) -> None:
        self._session = session
        self._settings = settings
        self._refunds = refunds
        self._returns = ReturnRepository(session)
        self._audits = AuditRepository(session)
        self._transitions = ReturnTransitions(AuditTrail(self._audits), clock)

    def queue(
        self, status: ReturnStatus | None, page: int, size: int
    ) -> PageResponse[ReturnSummaryResponse]:
        rows, total = self._returns.queue(status, (page - 1) * size, size)
        return PageResponse[ReturnSummaryResponse](
            items=[to_summary(return_request, updated_at) for return_request, updated_at in rows],
            total=total,
            page=page,
            size=size,
        )

    def detail(self, code: str) -> ReturnDetailResponse:
        return self._detail(self._find(code))

    def receive(self, code: str, agent: CurrentUser) -> ReturnDetailResponse:
        return_request = self._find(code, for_update=True)
        if return_request.status in AFTER_RECEIPT or _was_inspected(return_request):
            raise AlreadyReceivedError()
        actor = Actor.staff(agent)
        if return_request.status == ReturnStatus.APPROVED:
            # The parcel arrived before the customer pressed "I've shipped it".
            self._transitions.move(
                return_request,
                ReturnStatus.IN_TRANSIT,
                actor,
                note="Label scanned at the warehouse before the customer marked it shipped.",
            )
        self._transitions.move(
            return_request, ReturnStatus.RECEIVED, actor, note="Parcel scanned at the warehouse."
        )
        self._session.commit()
        return self._detail(self._returns.get_by_id(return_request.return_id))

    def inspect(
        self, code: str, agent: CurrentUser, payload: InspectionRequest
    ) -> InspectionResultResponse:
        return_request = self._find(code, for_update=True)
        if return_request.status != ReturnStatus.RECEIVED:
            if _was_inspected(return_request):
                raise InvalidTransitionError(
                    "Already inspected: another agent finished this return first. Reload it."
                )
            ensure_can_move(return_request.status, ReturnStatus.INSPECTED)

        items = {item.return_item_id: item for item in return_request.items}
        graded = [grade.return_item_id for grade in payload.items]
        if len(set(graded)) != len(graded):
            raise InspectionMismatchError("Each item can only be graded once.")
        if set(graded) - set(items):
            raise InspectionMismatchError("Some of these items are not part of this return.")
        missing = [items[item_id].order_item.product.name for item_id in set(items) - set(graded)]
        if missing:
            raise InspectionMismatchError(
                f"Grade every item before submitting. Missing: {', '.join(sorted(missing))}."
            )

        amounts = {}
        for grade in payload.items:
            item = items[grade.return_item_id]
            percent = refund_percent(grade.grade, grade.decision)
            self._session.add(
                Inspection(
                    return_item_id=item.return_item_id,
                    agent_id=agent.user_id,
                    grade=grade.grade,
                    decision=grade.decision,
                    refund_percent=percent,
                    notes=grade.notes,
                )
            )
            if percent:
                amounts[item.return_item_id] = refund_amount(
                    item.order_item.unit_price, item.quantity, percent
                )

        actor = Actor.staff(agent)
        needs_approval = False
        if not amounts:
            self._transitions.move(
                return_request,
                ReturnStatus.REJECTED,
                actor,
                note="Every item was rejected at inspection.",
            )
        else:
            total = refund_total(amounts.values())
            needs_approval = needs_finance_approval(
                total, self._settings.finance_approval_threshold_inr
            )
            for item_id, amount in amounts.items():
                self._session.add(
                    Refund(
                        return_item_id=item_id,
                        amount=amount,
                        method=return_request.refund_method,
                        requires_approval=needs_approval,
                        status=(
                            RefundStatus.PENDING_APPROVAL
                            if needs_approval
                            else RefundStatus.PROCESSING
                        ),
                        idempotency_key=f"refund-{item_id}",
                        attempt_count=0,
                    )
                )
            return_request.awaiting_finance = needs_approval
            self._transitions.move(
                return_request,
                ReturnStatus.INSPECTED,
                actor,
                note="Waiting for finance approval." if needs_approval else None,
                details={"refund_total": str(total)},
            )
        try:
            self._session.commit()
        except (IntegrityError, StaleDataError) as error:
            self._session.rollback()
            raise ConcurrentUpdateError() from error

        if amounts and not needs_approval:
            self._refunds.pay_return(return_request.return_id, Actor.system())
        return to_inspection_result(self._returns.get_by_id(return_request.return_id))

    def _find(self, code: str, *, for_update: bool = False) -> ReturnRequest:
        return_request = self._returns.get_by_code(code, for_update=for_update)
        if return_request is None:
            raise ReturnNotFoundError()
        return return_request

    def _detail(self, return_request: ReturnRequest) -> ReturnDetailResponse:
        return to_return_detail(
            return_request, self._audits.status_history(return_request.return_id)
        )


def _was_inspected(return_request: ReturnRequest) -> bool:
    return any(item.inspection is not None for item in return_request.items)
