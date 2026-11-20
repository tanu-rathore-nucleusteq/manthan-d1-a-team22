"""Repository protocols used by the services."""

from typing import Protocol

from returnright.models.order import Order


class OrderReader(Protocol):
    def find_by_number_and_email(self, order_number: str, email: str) -> Order | None:
        """The order with its items, products and categories loaded, or None when the number
        and email do not belong together."""
        ...
