"""Finance approval for returns whose refund total is above the threshold: the queue, and one
decision per return. Approval pays the refunds at once; rejection closes the return.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from returnright.core.exceptions import (
    AlreadyDecidedError,
    NoPendingApprovalError,
    ReturnNotFoundError,
)
from returnright.domain.enums import RefundStatus, ReturnStatus
from returnright.dtos.internal.audit import Actor
from returnright.dtos.internal.auth import CurrentUser
from returnright.dtos.responses.common import PageResponse
from returnright.dtos.responses.finance import PendingApprovalResponse
from returnright.mappers.refund_mapper import to_pending_approval
from returnright.models.refund import APPROVED, REJECTED, FinanceApproval
from returnright.repositories.audit_repository import AuditRepository
from returnright.repositories.refund_repository import RefundRepository
from returnright.repositories.return_repository import ReturnRepository
from returnright.services.audit_service import RETURN, AuditTrail, ReturnTransitions
from returnright.services.refund_service import RefundService
from returnright.utils.clock import Clock


class ApprovalService:
    def __init__(self, session: Session, clock: Clock, refunds: RefundService) -> None:
        self._session = session
        self._refund_service = refunds
        self._returns = ReturnRepository(session)
        self._refunds = RefundRepository(session)
        self._audit = AuditTrail(AuditRepository(session))
        self._transitions = ReturnTransitions(self._audit, clock)

    def queue(self, page: int, size: int) -> PageResponse[PendingApprovalResponse]:
        returns, total = self._returns.awaiting_finance((page - 1) * size, size)
        return PageResponse[PendingApprovalResponse](
            items=[to_pending_approval(return_request) for return_request in returns],
            total=total,
            page=page,
            size=size,
        )

    def decide(
        self, code: str, reviewer: CurrentUser, approve: bool, comment: str | None
    ) -> PendingApprovalResponse:
        return_request = self._returns.get_by_code(code, for_update=True)
        if return_request is None:
            raise ReturnNotFoundError()
        if return_request.approval is not None:
            raise AlreadyDecidedError()
        if not return_request.awaiting_finance or return_request.status != ReturnStatus.INSPECTED:
            raise NoPendingApprovalError()

        actor = Actor.staff(reviewer)
        self._refunds.add_approval(
            FinanceApproval(
                return_id=return_request.return_id,
                reviewer_id=reviewer.user_id,
                decision=APPROVED if approve else REJECTED,
                comment=comment,
            )
        )
        refunds = self._refunds.for_return(return_request.return_id, for_update=True)
        return_request.awaiting_finance = False
        if approve:
            for refund in refunds:
                if refund.status == RefundStatus.PENDING_APPROVAL:
                    refund.status = RefundStatus.APPROVED
            self._audit.record(
                entity_type=RETURN,
                entity_id=return_request.return_id,
                return_id=return_request.return_id,
                action="FINANCE_APPROVED",
                actor=actor,
                details={"comment": comment} if comment else None,
            )
        else:
            for refund in refunds:
                refund.status = RefundStatus.REJECTED
            self._transitions.move(
                return_request,
                ReturnStatus.REJECTED,
                actor,
                note=comment or "Finance rejected the refund.",
            )
        try:
            self._session.commit()
        except IntegrityError as error:  # a second reviewer decided at the same moment
            self._session.rollback()
            raise AlreadyDecidedError() from error

        if approve:
            self._refund_service.pay_return(return_request.return_id, actor)
        return to_pending_approval(self._returns.get_by_id(return_request.return_id))
