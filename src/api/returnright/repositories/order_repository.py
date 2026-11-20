"""Queries for orders, items, products and categories."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from returnright.models.catalog import Product
from returnright.models.customer import Customer
from returnright.models.order import Order, OrderItem


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_number_and_email(self, order_number: str, email: str) -> Order | None:
        """Email matching ignores case, like the unique index on lower(email)."""
        statement = (
            select(Order)
            .join(Order.customer)
            .where(Order.order_number == order_number)
            .where(func.lower(Customer.email) == email.lower())
            .options(
                selectinload(Order.items)
                .selectinload(OrderItem.product)
                .selectinload(Product.category)
            )
        )
        return self._session.scalars(statement).one_or_none()
