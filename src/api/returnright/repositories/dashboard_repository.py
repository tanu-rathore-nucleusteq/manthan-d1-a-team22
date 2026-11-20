"""Aggregates for the manager dashboard, computed in SQL. Dates are UTC calendar days and
both ends of a range are inclusive.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import ColumnElement, Select, exists, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from returnright.models import (
    Category,
    Customer,
    CustomerFlag,
    Order,
    OrderItem,
    Product,
    ReasonCode,
    ReturnItem,
    ReturnRequest,
)


@dataclass(frozen=True)
class CategoryCounts:
    category: str
    orders: int
    returns: int


@dataclass(frozen=True)
class FlaggedCustomerRow:
    customer_id: int
    name: str
    returns_in_window: int


def _utc_day(column: InstrumentedAttribute[datetime]) -> ColumnElement[date]:
    return func.date(func.timezone("UTC", column))


def _within(
    column: InstrumentedAttribute[datetime], date_from: date | None, date_to: date | None
) -> list[ColumnElement[bool]]:
    day = _utc_day(column)
    conditions = []
    if date_from is not None:
        conditions.append(day >= date_from)
    if date_to is not None:
        conditions.append(day <= date_to)
    return conditions


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def category_counts(self, date_from: date | None, date_to: date | None) -> list[CategoryCounts]:
        """Per category: orders containing one of its products, and returns of those items.
        Every category is listed, so a category nobody returns from shows 0.
        """
        orders = self._counts(
            select(Category.name, func.count(func.distinct(Order.order_id)))
            .join(Product, Product.category_id == Category.category_id)
            .join(OrderItem, OrderItem.product_id == Product.product_id)
            .join(Order, Order.order_id == OrderItem.order_id)
            .where(*_within(Order.ordered_at, date_from, date_to))
            .group_by(Category.name)
        )
        returns = self._counts(
            select(Category.name, func.count(func.distinct(ReturnItem.return_id)))
            .join(Product, Product.category_id == Category.category_id)
            .join(OrderItem, OrderItem.product_id == Product.product_id)
            .join(ReturnItem, ReturnItem.order_item_id == OrderItem.order_item_id)
            .join(ReturnRequest, ReturnRequest.return_id == ReturnItem.return_id)
            .where(
                ReturnItem.is_eligible.is_(True),
                *_within(ReturnRequest.requested_at, date_from, date_to),
            )
            .group_by(Category.name)
        )
        names = self._session.scalars(select(Category.name).order_by(Category.name))
        return [CategoryCounts(name, orders.get(name, 0), returns.get(name, 0)) for name in names]

    def _counts(self, statement: Select[tuple[str, int]]) -> dict[str, int]:
        return {name: count for name, count in self._session.execute(statement)}

    def reason_counts(
        self, date_from: date | None, date_to: date | None, limit: int | None = None
    ) -> list[tuple[str, int]]:
        """Reason codes by number of returned items, most used first."""
        count = func.count(ReturnItem.return_item_id)
        statement = (
            select(ReasonCode.code, count)
            .join(ReturnItem, ReturnItem.reason_id == ReasonCode.reason_id)
            .join(ReturnRequest, ReturnRequest.return_id == ReturnItem.return_id)
            .where(
                ReturnItem.is_eligible.is_(True),
                *_within(ReturnRequest.requested_at, date_from, date_to),
            )
            .group_by(ReasonCode.code)
            .order_by(count.desc(), ReasonCode.code)
            .limit(limit)
        )
        return [(code, count) for code, count in self._session.execute(statement)]

    def average_cycle_hours(self, date_from: date | None, date_to: date | None) -> float | None:
        """Mean hours from request to refund or rejection, over closed returns."""
        hours = func.extract("epoch", ReturnRequest.closed_at - ReturnRequest.requested_at) / 3600
        value = self._session.scalar(
            select(func.avg(hours)).where(
                ReturnRequest.closed_at.is_not(None),
                *_within(ReturnRequest.requested_at, date_from, date_to),
            )
        )
        return None if value is None else round(float(value), 1)

    def flagged_customers(self, window_start: date) -> list[FlaggedCustomerRow]:
        """Customers with an open flag, with their returns requested since `window_start`."""
        recent = (
            select(func.count(ReturnRequest.return_id))
            .where(
                ReturnRequest.customer_id == Customer.customer_id,
                _utc_day(ReturnRequest.requested_at) >= window_start,
            )
            .correlate(Customer)
            .scalar_subquery()
            .label("returns_in_window")
        )
        open_flag = exists().where(
            CustomerFlag.customer_id == Customer.customer_id, CustomerFlag.resolved_at.is_(None)
        )
        statement = (
            select(Customer.customer_id, Customer.full_name, recent)
            .where(open_flag)
            .order_by(recent.desc(), Customer.full_name)
        )
        return [FlaggedCustomerRow(*row) for row in self._session.execute(statement)]
