"""Finds an order by number and email and runs the eligibility engine on its items."""

from returnright.core.exceptions import OrderNotFoundError
from returnright.domain.eligibility import EligibilityDecision, decide_eligibility
from returnright.dtos.responses.orders import OrderLookupResponse
from returnright.interfaces.repositories import OrderReader
from returnright.mappers.order_mapper import to_order_lookup_response
from returnright.models.order import Order
from returnright.utils.clock import Clock, to_utc_date


def decide_items(order: Order, clock: Clock) -> dict[int, EligibilityDecision]:
    """BR 1.2: innerwear and perishables are never returnable; every other item gets its
    category's window (10 days for electronics, otherwise the standard 30 days), counted from
    the delivery date. A mixed basket is decided per item. Keyed by order_item_id; used by the
    lookup and again when a return is created, so both always agree.
    """
    today = clock.today()
    delivered_on = to_utc_date(order.delivered_at)
    decisions = {}
    for item in order.items:
        category = item.product.category
        decisions[item.order_item_id] = decide_eligibility(
            delivered_on,
            today,
            category=category.name,
            is_returnable=category.is_returnable,
            window_days=category.return_window_days,
        )
    return decisions


class OrderService:
    def __init__(self, orders: OrderReader, clock: Clock) -> None:
        self._orders = orders
        self._clock = clock

    def lookup(self, order_number: str, email: str) -> OrderLookupResponse:
        order = self._orders.find_by_number_and_email(order_number, email)
        if order is None:
            raise OrderNotFoundError()
        return to_order_lookup_response(order, decide_items(order, self._clock))
