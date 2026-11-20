"""Queries for customers and their frequent-returner flags."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from returnright.models.customer import Customer, CustomerFlag


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, customer_id: int) -> Customer | None:
        return self._session.get(Customer, customer_id)

    def has_open_flag(self, customer_id: int) -> bool:
        statement = select(CustomerFlag.flag_id).where(
            CustomerFlag.customer_id == customer_id, CustomerFlag.resolved_at.is_(None)
        )
        return self._session.scalar(statement) is not None

    def add_flag(self, flag: CustomerFlag) -> None:
        self._session.add(flag)
