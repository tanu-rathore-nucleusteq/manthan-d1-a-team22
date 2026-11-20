"""Finds an order by number and email and runs the eligibility engine on its items."""

from returnright.core.exceptions import OrderNotFoundError
from returnright.domain.eligibility import CategoryRule, EligibilityDecision, check_item
from returnright.dtos.responses.orders import OrderLookupResponse
from returnright.interfaces.repositories import OrderReader
from returnright.mappers.order_mapper import to_order_lookup_response
from returnright.models.catalog import Category
from returnright.models.order import Order
from returnright.utils.clock import Clock, to_utc_date


def decide_items(order: Order, clock: Clock) -> dict[int, EligibilityDecision]:
    """Eligibility for every item of the order, keyed by order_item_id. Each item gets its
    category's rule and window, counted from the delivery date."""
    today = clock.today()
    delivered_on = to_utc_date(order.delivered_at)
    return {
        item.order_item_id: check_item(category_rule(item.product.category), delivered_on, today)
        for item in order.items
    }


def category_rule(category: Category) -> CategoryRule:
    return CategoryRule(
        name=category.name,
        is_returnable=category.is_returnable,
        window_days=category.return_window_days,
    )


class OrderService:
    def __init__(self, orders: OrderReader, clock: Clock) -> None:
        self._orders = orders
        self._clock = clock

    def lookup(self, order_number: str, email: str) -> OrderLookupResponse:
        order = self._orders.find_by_number_and_email(order_number, email)
        if order is None:
            raise OrderNotFoundError()
        return to_order_lookup_response(order, decide_items(order, self._clock))
