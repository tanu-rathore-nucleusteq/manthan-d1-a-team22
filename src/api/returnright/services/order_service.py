"""Finds an order by number and email and runs the eligibility engine on its items."""

from returnright.core.exceptions import OrderNotFoundError
from returnright.domain.eligibility import check_return_window
from returnright.dtos.responses.orders import OrderLookupResponse
from returnright.interfaces.repositories import OrderReader
from returnright.mappers.order_mapper import to_order_lookup_response
from returnright.utils.clock import Clock, to_utc_date


class OrderService:
    def __init__(self, orders: OrderReader, clock: Clock) -> None:
        self._orders = orders
        self._clock = clock

    def lookup(self, order_number: str, email: str) -> OrderLookupResponse:
        """BR 1.2: every item gets the standard 30-day window, counted from the delivery date."""
        order = self._orders.find_by_number_and_email(order_number, email)
        if order is None:
            raise OrderNotFoundError()

        today = self._clock.today()
        delivered_on = to_utc_date(order.delivered_at)
        decisions = {
            item.order_item_id: check_return_window(delivered_on, today) for item in order.items
        }
        return to_order_lookup_response(order, decisions)
