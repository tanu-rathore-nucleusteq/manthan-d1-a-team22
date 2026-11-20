"""OrderRepository against the real PostgreSQL in DATABASE_URL; skipped when it is not running.
Each test inserts its rows inside a transaction that is rolled back afterwards.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from returnright.db.session import get_engine, get_session_factory
from returnright.models import Category, Customer, Order, OrderItem, Product
from returnright.repositories.order_repository import OrderRepository
from returnright.services.order_service import OrderService
from returnright.utils.clock import FixedClock

NOW = datetime(2026, 11, 20, 9, 30, tzinfo=UTC)


@pytest.fixture
def session():
    try:
        with get_engine().connect():
            pass
    except OperationalError:
        pytest.skip("PostgreSQL is not reachable at DATABASE_URL")
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def order(session):
    apparel = session.scalars(select(Category).where(Category.name == "Apparel")).one()
    customer = Customer(full_name="Asha Test", email="Asha.BR12@Example.com")
    product = Product(
        sku="BR12-SHIRT",
        name="Cotton shirt",
        category_id=apparel.category_id,
        price=Decimal("1499.00"),
    )
    session.add_all([customer, product])
    session.flush()
    order = Order(
        order_number="BR12-DAY30",
        customer_id=customer.customer_id,
        payment_method="UPI",
        ordered_at=NOW - timedelta(days=33),
        delivered_at=NOW - timedelta(days=30),
        total_amount=Decimal("1499.00"),
    )
    session.add(order)
    session.flush()
    session.add(
        OrderItem(
            order_id=order.order_id,
            product_id=product.product_id,
            quantity=1,
            unit_price=Decimal("1499.00"),
        )
    )
    session.flush()
    session.expunge_all()  # force the repository to load everything from the database
    return order


def test_finds_order_by_number_and_email_ignoring_case(session, order):
    found = OrderRepository(session).find_by_number_and_email("BR12-DAY30", "asha.br12@example.com")

    assert found is not None
    assert found.items[0].product.category.name == "Apparel"


def test_wrong_email_finds_nothing(session, order):
    assert OrderRepository(session).find_by_number_and_email("BR12-DAY30", "x@example.com") is None


def test_lookup_on_day_30_is_returnable_end_to_end(session, order):
    service = OrderService(OrderRepository(session), FixedClock(NOW))

    result = service.lookup("BR12-DAY30", "asha.br12@example.com")

    assert result.items[0].eligible is True
    assert str(result.items[0].window_ends_on) == "2026-11-20"
