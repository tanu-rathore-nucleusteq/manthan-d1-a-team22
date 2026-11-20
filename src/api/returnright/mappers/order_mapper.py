"""Order and order items to OrderLookupResponse."""

from collections.abc import Mapping

from returnright.domain.eligibility import EligibilityDecision
from returnright.dtos.responses.orders import ItemEligibilityResponse, OrderLookupResponse
from returnright.models.order import Order
from returnright.utils.clock import to_utc_date


def to_order_lookup_response(
    order: Order, decisions: Mapping[int, EligibilityDecision]
) -> OrderLookupResponse:
    """`decisions` is keyed by order_item_id."""
    return OrderLookupResponse(
        order_number=order.order_number,
        delivered_on=to_utc_date(order.delivered_at),
        items=[
            ItemEligibilityResponse(
                order_item_id=item.order_item_id,
                product_name=item.product.name,
                category=item.product.category.name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                eligible=decisions[item.order_item_id].eligible,
                reason=decisions[item.order_item_id].reason,
                window_ends_on=decisions[item.order_item_id].window_ends_on,
            )
            for item in order.items
        ],
    )
