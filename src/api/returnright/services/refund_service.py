"""Pays each refund exactly once: one refund per return item, the key refund-<return_item_id> on
every gateway call, and one ledger row. Store credit goes to the ledger only, never the gateway.
A gateway error marks the refund failed and a retry reuses the same key; a timeout is retried the
same way, because the gateway replays its first answer for a key it has already paid.

Locks are always taken in the same order, the return first and then the refund, so two payments
of the same return can't deadlock. The gateway is called between transactions, never inside one.
"""

from sqlalchemy.orm import Session

from returnright.core.exceptions import RefundNotFoundError, RefundNotPayableError
from returnright.domain.enums import LedgerEntryType, RefundMethod, RefundStatus, ReturnStatus
from returnright.dtos.internal.audit import Actor
from returnright.dtos.internal.payments import GatewayPaymentRequest
from returnright.dtos.responses.common import PageResponse
from returnright.dtos.responses.finance import LedgerEntryResponse, RefundResponse
from returnright.interfaces.payment_gateway import GatewayUnavailableError, PaymentGateway
from returnright.mappers.refund_mapper import to_ledger_response, to_refund_response
from returnright.models.ledger import LedgerEntry
from returnright.models.refund import Refund
from returnright.models.return_request import ReturnRequest
from returnright.repositories.audit_repository import AuditRepository
from returnright.repositories.ledger_repository import LedgerRepository
from returnright.repositories.refund_repository import RefundRepository
from returnright.repositories.return_repository import ReturnRepository
from returnright.services.audit_service import AuditTrail, ReturnTransitions
from returnright.utils.clock import Clock

REFUND = "REFUND"
PAYABLE = {RefundStatus.APPROVED, RefundStatus.PROCESSING, RefundStatus.FAILED}


class RefundService:
    def __init__(self, session: Session, gateway: PaymentGateway, clock: Clock) -> None:
        self._session = session
        self._gateway = gateway
        self._clock = clock
        self._refunds = RefundRepository(session)
        self._returns = ReturnRepository(session)
        self._ledger = LedgerRepository(session)
        self._audit = AuditTrail(AuditRepository(session))
        self._transitions = ReturnTransitions(self._audit, clock)

    # --- read --------------------------------------------------------------------------------

    def page(
        self, status: RefundStatus | None, page: int, size: int
    ) -> PageResponse[RefundResponse]:
        refunds, total = self._refunds.page(status, (page - 1) * size, size)
        return PageResponse[RefundResponse](
            items=[self.response(refund) for refund in refunds], total=total, page=page, size=size
        )

    def detail(self, refund_id: int) -> RefundResponse:
        refund = self._refunds.get(refund_id)
        if refund is None:
            raise RefundNotFoundError()
        return self.response(refund)

    def ledger(
        self, refund_id: int | None, page: int, size: int
    ) -> PageResponse[LedgerEntryResponse]:
        entries, total = self._ledger.page(refund_id, (page - 1) * size, size)
        return PageResponse[LedgerEntryResponse](
            items=[to_ledger_response(entry) for entry in entries],
            total=total,
            page=page,
            size=size,
        )

    def response(self, refund: Refund) -> RefundResponse:
        """RefundResponse for a refund loaded with its return (RefundRepository.get or page)."""
        return to_refund_response(refund, refund.return_item.return_request)

    # --- pay ---------------------------------------------------------------------------------

    def pay_and_describe(self, refund_id: int, actor: Actor, request_key: str) -> RefundResponse:
        """The retry endpoint: pay (or replay) the refund, then return its current state."""
        self.pay(refund_id, actor, request_key)
        return self.detail(refund_id)

    def pay_return(self, return_id: int, actor: Actor) -> None:
        """Pay every refund of the return that is ready to be paid."""
        for refund in self._refunds.for_return(return_id):
            if refund.status in PAYABLE:
                self.pay(refund.refund_id, actor)

    def pay(self, refund_id: int, actor: Actor, request_key: str | None = None) -> Refund:
        """Pay one refund, or retry a failed one. Safe to call any number of times."""
        refund = self._claim(refund_id, actor, request_key)
        if refund.status == RefundStatus.PAID:
            return refund
        if refund.method == RefundMethod.STORE_CREDIT:
            return self._settle(refund_id, None, actor)
        try:
            result = self._gateway.pay(
                GatewayPaymentRequest(
                    refund_id=refund.refund_id,
                    amount=refund.amount,
                    idempotency_key=refund.idempotency_key,
                )
            )
        except GatewayUnavailableError as error:
            return self._fail(refund_id, actor, str(error))
        if result.status != "succeeded":
            return self._fail(refund_id, actor, "The gateway declined the payment.")
        return self._settle(refund_id, result.transaction_id, actor)

    def _lock(self, refund_id: int) -> tuple[ReturnRequest, Refund]:
        return_id = self._refunds.return_id_of(refund_id)
        if return_id is None:
            raise RefundNotFoundError()
        return_request = self._returns.get_by_id(return_id, for_update=True)
        return return_request, self._refunds.get(refund_id, for_update=True)

    def _claim(self, refund_id: int, actor: Actor, request_key: str | None) -> Refund:
        return_request, refund = self._lock(refund_id)
        return_id = return_request.return_id
        if refund.status == RefundStatus.PAID:
            self._session.commit()
            return refund
        if refund.status == RefundStatus.PENDING_APPROVAL:
            raise RefundNotPayableError("This refund is waiting for a finance decision.")
        if refund.status == RefundStatus.REJECTED:
            raise RefundNotPayableError("Finance rejected this refund, so it can't be paid.")

        previous = refund.status
        refund.status = RefundStatus.PROCESSING
        refund.attempt_count += 1
        details: dict[str, object] = {"attempt": refund.attempt_count}
        if request_key:
            details["request_key"] = request_key
        self._audit.record(
            entity_type=REFUND,
            entity_id=refund_id,
            return_id=return_id,
            action="PAYMENT_STARTED",
            actor=actor,
            old_status=previous.name,
            new_status=RefundStatus.PROCESSING.name,
            details=details,
        )
        self._session.commit()
        return refund

    def _settle(self, refund_id: int, transaction_id: str | None, actor: Actor) -> Refund:
        return_request, refund = self._lock(refund_id)
        return_id = return_request.return_id
        if refund.status == RefundStatus.PAID:  # a concurrent call finished first
            self._session.commit()
            return refund

        refund.status = RefundStatus.PAID
        refund.gateway_reference = transaction_id
        refund.paid_at = self._clock.now()
        self._ledger.add(
            LedgerEntry(
                refund_id=refund_id,
                customer_id=return_request.customer_id,
                entry_type=LedgerEntryType.REFUND,
                amount=refund.amount,
                method=refund.method,
                gateway_reference=transaction_id,
            )
        )
        self._audit.record(
            entity_type=REFUND,
            entity_id=refund_id,
            return_id=return_id,
            action="PAID",
            actor=actor,
            old_status=RefundStatus.PROCESSING.name,
            new_status=RefundStatus.PAID.name,
            details={"amount": str(refund.amount), "gateway_reference": transaction_id},
        )
        all_paid = all(
            other.status == RefundStatus.PAID for other in self._refunds.for_return(return_id)
        )
        if all_paid and return_request.status == ReturnStatus.INSPECTED:
            self._transitions.move(
                return_request, ReturnStatus.REFUNDED, actor, note="Refund paid."
            )
        self._session.commit()
        return refund

    def _fail(self, refund_id: int, actor: Actor, error: str) -> Refund:
        return_request, refund = self._lock(refund_id)
        return_id = return_request.return_id
        if refund.status == RefundStatus.PAID:
            self._session.commit()
            return refund
        refund.status = RefundStatus.FAILED
        self._audit.record(
            entity_type=REFUND,
            entity_id=refund_id,
            return_id=return_id,
            action="PAYMENT_FAILED",
            actor=actor,
            old_status=RefundStatus.PROCESSING.name,
            new_status=RefundStatus.FAILED.name,
            details={"error": error[:200]},
        )
        self._session.commit()
        return refund
