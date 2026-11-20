"""Queries for return requests, their items, photos, inspections and refunds."""

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from returnright.domain.enums import ReturnStatus
from returnright.models import (
    AuditLog,
    FinanceApproval,
    OrderItem,
    Product,
    ReasonCode,
    ReturnItem,
    ReturnRequest,
)


def detail_options() -> tuple[LoaderOption, ...]:
    """Everything a return detail, inspection or approval screen shows."""
    items = selectinload(ReturnRequest.items)
    return (
        selectinload(ReturnRequest.order),
        selectinload(ReturnRequest.customer),
        selectinload(ReturnRequest.approval).selectinload(FinanceApproval.reviewer),
        items.selectinload(ReturnItem.order_item)
        .selectinload(OrderItem.product)
        .selectinload(Product.category),
        items.selectinload(ReturnItem.reason),
        items.selectinload(ReturnItem.photos),
        items.selectinload(ReturnItem.inspection),
        items.selectinload(ReturnItem.refund),
    )


def _load(statement: Select, for_update: bool) -> Select:
    # populate_existing refreshes objects already in the session, so a reload after a commit
    # always shows the database's current state.
    statement = statement.options(*detail_options()).execution_options(populate_existing=True)
    return statement.with_for_update(of=ReturnRequest) if for_update else statement


class ReturnRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, return_request: ReturnRequest) -> None:
        self._session.add(return_request)

    def get_by_code(self, code: str, *, for_update: bool = False) -> ReturnRequest | None:
        statement = select(ReturnRequest).where(ReturnRequest.return_code == code.upper())
        return self._session.scalars(_load(statement, for_update)).one_or_none()

    def get_by_id(self, return_id: int, *, for_update: bool = False) -> ReturnRequest | None:
        statement = select(ReturnRequest).where(ReturnRequest.return_id == return_id)
        return self._session.scalars(_load(statement, for_update)).one_or_none()

    def queue(
        self, status: ReturnStatus | None, offset: int, limit: int
    ) -> tuple[list[tuple[ReturnRequest, datetime | None]], int]:
        """Returns oldest first, each with the time of its last audit entry."""
        last_change = (
            select(func.max(AuditLog.created_at))
            .where(AuditLog.return_id == ReturnRequest.return_id)
            .correlate(ReturnRequest)
            .scalar_subquery()
        )
        conditions = [ReturnRequest.status == status] if status is not None else []
        total = self._session.scalar(
            select(func.count()).select_from(ReturnRequest).where(*conditions)
        )
        rows = self._session.execute(
            select(ReturnRequest, last_change)
            .where(*conditions)
            .options(
                selectinload(ReturnRequest.order),
                selectinload(ReturnRequest.customer),
                selectinload(ReturnRequest.items).selectinload(ReturnItem.refund),
            )
            .order_by(ReturnRequest.requested_at, ReturnRequest.return_id)
            .offset(offset)
            .limit(limit)
        ).all()
        return [(row[0], row[1]) for row in rows], total or 0

    def awaiting_finance(self, offset: int, limit: int) -> tuple[list[ReturnRequest], int]:
        conditions = [
            ReturnRequest.awaiting_finance.is_(True),
            ReturnRequest.status == ReturnStatus.INSPECTED,
        ]
        total = self._session.scalar(
            select(func.count()).select_from(ReturnRequest).where(*conditions)
        )
        statement = (
            select(ReturnRequest)
            .where(*conditions)
            .options(*detail_options())
            .order_by(ReturnRequest.requested_at, ReturnRequest.return_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(statement)), total or 0

    def count_customer_returns_since(self, customer_id: int, since: datetime) -> int:
        statement = (
            select(func.count())
            .select_from(ReturnRequest)
            .where(ReturnRequest.customer_id == customer_id, ReturnRequest.requested_at >= since)
        )
        return self._session.scalar(statement) or 0

    def order_items_already_returned(self, order_item_ids: list[int]) -> set[int]:
        """Order items that are already in an eligible return item, whatever its status."""
        statement = select(ReturnItem.order_item_id).where(
            ReturnItem.order_item_id.in_(order_item_ids), ReturnItem.is_eligible.is_(True)
        )
        return set(self._session.scalars(statement))

    def reason_ids(self) -> dict[str, int]:
        return {row.code: row.reason_id for row in self._session.scalars(select(ReasonCode))}
