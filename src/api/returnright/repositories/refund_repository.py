"""Queries for refunds and finance approvals."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from returnright.domain.enums import RefundStatus
from returnright.models import FinanceApproval, Refund, ReturnItem, ReturnRequest


def _with_return() -> LoaderOption:
    """A refund with its return and the finance decision, for RefundResponse."""
    return (
        selectinload(Refund.return_item)
        .selectinload(ReturnItem.return_request)
        .selectinload(ReturnRequest.approval)
        .selectinload(FinanceApproval.reviewer)
    )


class RefundRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, refund: Refund) -> None:
        self._session.add(refund)

    def return_id_of(self, refund_id: int) -> int | None:
        statement = (
            select(ReturnItem.return_id)
            .join(Refund, Refund.return_item_id == ReturnItem.return_item_id)
            .where(Refund.refund_id == refund_id)
        )
        return self._session.scalar(statement)

    def get(self, refund_id: int, *, for_update: bool = False) -> Refund | None:
        statement = (
            select(Refund)
            .where(Refund.refund_id == refund_id)
            .options(_with_return())
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update(of=Refund)
        return self._session.scalars(statement).one_or_none()

    def for_return(self, return_id: int, *, for_update: bool = False) -> list[Refund]:
        statement = (
            select(Refund)
            .join(ReturnItem, Refund.return_item_id == ReturnItem.return_item_id)
            .where(ReturnItem.return_id == return_id)
            .order_by(Refund.refund_id)
        )
        if for_update:
            statement = statement.with_for_update(of=Refund)
        return list(self._session.scalars(statement))

    def page(
        self, status: RefundStatus | None, offset: int, limit: int
    ) -> tuple[list[Refund], int]:
        conditions = [Refund.status == status] if status is not None else []
        total = self._session.scalar(select(func.count()).select_from(Refund).where(*conditions))
        statement = (
            select(Refund)
            .where(*conditions)
            .options(_with_return())
            .order_by(Refund.created_at.desc(), Refund.refund_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(statement)), total or 0

    def add_approval(self, approval: FinanceApproval) -> None:
        self._session.add(approval)
