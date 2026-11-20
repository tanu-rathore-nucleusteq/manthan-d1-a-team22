"""OrderRepository against the real PostgreSQL in DATABASE_URL; skipped when it is not running.
Each test inserts its rows inside a transaction that is rolled back afterwards. Every run uses
unique order numbers, SKUs and emails, so the tests never clash with seed or sample data.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from returnright.db.session import get_engine, get_session_factory
from returnright.domain.eligibility import (
    ELECTRONICS_RETURN_WINDOW_DAYS,
    NON_RETURNABLE_CATEGORIES,
)
from returnright.models import Category, Customer, Order, OrderItem, Product
from returnright.repositories.order_repository import OrderRepository
from returnright.services.order_service import OrderService
from returnright.utils.clock import FixedClock

NOW = datetime(2026, 11, 20, 9, 30, tzinfo=UTC)


@dataclass(frozen=True)
class SavedOrder:
    order_number: str
    email: str


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


def save_order(session: Session, delivered_days_ago: int, *categories: str) -> SavedOrder:
    """One order delivered `delivered_days_ago` days before NOW, one item per category name."""
    uid = uuid4().hex[:8].upper()
    by_name = {c.name: c for c in session.scalars(select(Category)).all()}
    customer = Customer(full_name="Integration Test", email=f"It.{uid}@Example.com")
    products = [
        Product(
            sku=f"IT-{uid}-{index}",
            name=f"{name} item",
            category_id=by_name[name].category_id,
            price=Decimal("1000.00"),
        )
        for index, name in enumerate(categories)
    ]
    session.add_all([customer, *products])
    session.flush()
    order = Order(
        order_number=f"IT-{uid}",
        customer_id=customer.customer_id,
        payment_method="UPI",
        ordered_at=NOW - timedelta(days=delivered_days_ago + 3),
        delivered_at=NOW - timedelta(days=delivered_days_ago),
        total_amount=Decimal("1000.00") * len(products),
    )
    session.add(order)
    session.flush()
    session.add_all(
        OrderItem(
            order_id=order.order_id,
            product_id=product.product_id,
            quantity=1,
            unit_price=product.price,
        )
        for product in products
    )
    session.flush()
    session.expunge_all()  # force the repository to load everything from the database
    return SavedOrder(order_number=order.order_number, email=f"it.{uid.lower()}@example.com")


def lookup(session: Session, saved: SavedOrder):
    return OrderService(OrderRepository(session), FixedClock(NOW)).lookup(
        saved.order_number, saved.email
    )


def test_finds_order_by_number_and_email_ignoring_case(session):
    saved = save_order(session, 30, "Apparel")

    found = OrderRepository(session).find_by_number_and_email(saved.order_number, saved.email)

    assert found is not None
    assert found.items[0].product.category.name == "Apparel"


def test_wrong_email_finds_nothing(session):
    saved = save_order(session, 30, "Apparel")

    repository = OrderRepository(session)

    assert repository.find_by_number_and_email(saved.order_number, "x@example.com") is None


def test_lookup_on_day_30_is_returnable_end_to_end(session):
    result = lookup(session, save_order(session, 30, "Apparel"))

    assert result.items[0].eligible is True
    assert str(result.items[0].window_ends_on) == "2026-11-20"


def test_electronics_category_in_the_database_has_a_10_day_window(session):
    electronics = session.scalars(select(Category).where(Category.name == "Electronics")).one()

    assert electronics.return_window_days == ELECTRONICS_RETURN_WINDOW_DAYS


@pytest.mark.parametrize(("days_ago", "phone_eligible"), [(10, True), (11, False)])
def test_electronics_window_end_to_end(session, days_ago, phone_eligible):
    result = lookup(session, save_order(session, days_ago, "Electronics", "Apparel"))

    decided = {item.category: item.eligible for item in result.items}
    assert decided == {"Electronics": phone_eligible, "Apparel": True}


def test_non_returnable_categories_in_the_database_match_the_rule(session):
    blocked = session.scalars(select(Category.name).where(Category.is_returnable.is_(False))).all()

    assert frozenset(blocked) == NON_RETURNABLE_CATEGORIES


def test_innerwear_and_perishables_refused_end_to_end(session):
    result = lookup(session, save_order(session, 1, "Innerwear", "Perishables", "Apparel"))

    decided = {item.category: item.eligible for item in result.items}
    assert decided == {"Innerwear": False, "Perishables": False, "Apparel": True}
