"""POST /api/v1/orders/lookup applies each item's return window (BR 1.2): 30 days by default,
10 days for electronics, decided per item in a mixed basket.

The repository is replaced by an in-memory fake and the clock is fixed, so no database is needed.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from returnright.api.deps import get_order_service
from returnright.main import app
from returnright.services.order_service import OrderService
from returnright.utils.clock import FixedClock

NOW = datetime(2026, 11, 20, 9, 30, tzinfo=UTC)
EMAIL = "asha@example.com"


def make_order(order_number: str, delivered_days_ago: int | None) -> SimpleNamespace:
    delivered_at = None if delivered_days_ago is None else NOW - timedelta(days=delivered_days_ago)
    apparel = SimpleNamespace(name="Apparel", return_window_days=30)
    return SimpleNamespace(
        order_number=order_number,
        delivered_at=delivered_at,
        items=[
            SimpleNamespace(
                order_item_id=11,
                quantity=1,
                unit_price=Decimal("1499.00"),
                product=SimpleNamespace(name="Cotton shirt", category=apparel),
            ),
            SimpleNamespace(
                order_item_id=12,
                quantity=2,
                unit_price=Decimal("799.50"),
                product=SimpleNamespace(name="Linen trousers", category=apparel),
            ),
        ],
    )


def make_mixed_order(order_number: str, delivered_days_ago: int) -> SimpleNamespace:
    """A phone (Electronics, 10 days) and a shirt (Apparel, 30 days) in one order."""
    return SimpleNamespace(
        order_number=order_number,
        delivered_at=NOW - timedelta(days=delivered_days_ago),
        items=[
            SimpleNamespace(
                order_item_id=21,
                quantity=1,
                unit_price=Decimal("24999.00"),
                product=SimpleNamespace(
                    name="Smartphone",
                    category=SimpleNamespace(name="Electronics", return_window_days=10),
                ),
            ),
            SimpleNamespace(
                order_item_id=22,
                quantity=1,
                unit_price=Decimal("1499.00"),
                product=SimpleNamespace(
                    name="Cotton shirt",
                    category=SimpleNamespace(name="Apparel", return_window_days=30),
                ),
            ),
        ],
    )


class FakeOrders:
    def __init__(self, *orders: SimpleNamespace) -> None:
        self._orders = {order.order_number: order for order in orders}

    def find_by_number_and_email(self, order_number: str, email: str):
        return self._orders.get(order_number) if email.lower() == EMAIL else None


@pytest.fixture
def client():
    orders = FakeOrders(
        make_order("ORD-DAY30", 30),
        make_order("ORD-DAY31", 31),
        make_order("ORD-NOTDLV", None),
        make_mixed_order("ORD-MIX10", 10),
        make_mixed_order("ORD-MIX11", 11),
    )
    app.dependency_overrides[get_order_service] = lambda: OrderService(orders, FixedClock(NOW))
    yield TestClient(app)
    app.dependency_overrides.clear()


def lookup(client: TestClient, order_number: str, email: str = EMAIL):
    return client.post("/api/v1/orders/lookup", json={"order_number": order_number, "email": email})


def test_day_30_items_are_returnable(client):
    response = lookup(client, "ORD-DAY30")

    assert response.status_code == 200
    body = response.json()
    assert body["order_number"] == "ORD-DAY30"
    assert body["delivered_on"] == "2026-10-21"
    assert [item["eligible"] for item in body["items"]] == [True, True]
    assert body["items"][0]["window_ends_on"] == "2026-11-20"
    assert body["items"][0]["reason"].startswith("You can return this item until 20 Nov 2026")


def test_day_31_items_are_not_returnable(client):
    body = lookup(client, "ORD-DAY31").json()

    assert [item["eligible"] for item in body["items"]] == [False, False]
    assert body["items"][0]["reason"].startswith("The 30-day return window ended on 19 Nov 2026")


def test_response_carries_item_details(client):
    item = lookup(client, "ORD-DAY30").json()["items"][1]

    assert item == {
        "order_item_id": 12,
        "product_name": "Linen trousers",
        "category": "Apparel",
        "unit_price": "799.50",
        "quantity": 2,
        "eligible": True,
        "reason": item["reason"],
        "window_ends_on": "2026-11-20",
    }


def test_undelivered_order_items_are_not_returnable(client):
    body = lookup(client, "ORD-NOTDLV").json()

    assert body["delivered_on"] is None
    assert all(item["eligible"] is False for item in body["items"])
    assert all(item["window_ends_on"] is None for item in body["items"])


def test_email_is_matched_without_case(client):
    assert lookup(client, "ORD-DAY30", "ASHA@Example.com").status_code == 200


@pytest.mark.parametrize(
    ("order_number", "email"), [("ORD-UNKNOWN", EMAIL), ("ORD-DAY30", "someone@example.com")]
)
def test_unknown_order_or_wrong_email_is_404_with_the_same_message(client, order_number, email):
    response = lookup(client, order_number, email)

    assert response.status_code == 404
    assert response.json() == {
        "code": "order_not_found",
        "message": "We couldn't find an order with that order number and email.",
        "request_id": None,
    }


def test_request_id_header_is_echoed_in_errors(client):
    response = client.post(
        "/api/v1/orders/lookup",
        json={"order_number": "ORD-UNKNOWN", "email": EMAIL},
        headers={"X-Request-ID": "req-123"},
    )

    assert response.json()["request_id"] == "req-123"


def eligibility_by_product(body: dict) -> dict[str, bool]:
    return {item["product_name"]: item["eligible"] for item in body["items"]}


def test_electronics_on_day_10_are_still_returnable(client):
    body = lookup(client, "ORD-MIX10").json()

    assert eligibility_by_product(body) == {"Smartphone": True, "Cotton shirt": True}
    phone = body["items"][0]
    assert phone["window_ends_on"] == "2026-11-20"
    assert phone["reason"].endswith("Electronics items have a 10-day return window.")


def test_electronics_on_day_11_are_refused_but_the_shirt_is_not(client):
    body = lookup(client, "ORD-MIX11").json()

    assert eligibility_by_product(body) == {"Smartphone": False, "Cotton shirt": True}
    phone, shirt = body["items"]
    assert phone["reason"] == (
        "Electronics items have a 10-day return window, which ended on 19 Nov 2026. "
        "This item was delivered 11 days ago."
    )
    assert shirt["window_ends_on"] == "2026-12-09"  # delivered 9 Nov + 30 days
