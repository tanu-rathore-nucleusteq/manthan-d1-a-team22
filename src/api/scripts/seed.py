"""Seed synthetic data with Faker seed 42: 2,000 orders, 40 products in 6 categories, 500
customers, one staff user per role (warehouse1, finance1, manager1; password from DEMO_PASSWORD)
and the demo orders in docs/implementation-plan.md section 7, dated relative to the day the seed
runs. --if-empty skips seeding when data exists; without it the script truncates and reloads.

Run from src/api:  python -m scripts.seed [--if-empty]
"""

import argparse
import random
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from returnright.core.config import get_settings
from returnright.core.security import hash_password
from returnright.db.session import session_scope
from returnright.domain.enums import RefundMethod, ReturnReason, ReturnStatus, Role
from returnright.models import (
    AuditLog,
    Category,
    Customer,
    Order,
    OrderItem,
    Product,
    ReasonCode,
    ReturnItem,
    ReturnRequest,
    StaffUser,
)
from returnright.models.audit_log import STATUS_CHANGE
from returnright.utils.ids import new_return_code

SEED = 42
CUSTOMERS = 500
ORDERS = 2000
PAYMENT_METHODS = ("CARD", "UPI", "NETBANKING", "COD")

# 40 products in 6 categories; the demo orders below use several of them by name.
CATALOGUE: dict[str, list[tuple[str, str]]] = {
    "Electronics": [
        ("Smartphone A52", "8000.00"),
        ("Wireless earbuds", "2500.00"),
        ("Laptop 14 inch", "12000.00"),
        ("Smartwatch", "4500.00"),
        ("Bluetooth speaker", "3200.00"),
        ("Power bank", "1500.00"),
        ("Tablet 10 inch", "15000.00"),
    ],
    "Apparel": [
        ("Cotton shirt", "1500.00"),
        ("Denim jeans", "2200.00"),
        ("Rain jacket", "2000.00"),
        ("Linen trousers", "1600.00"),
        ("Kurta", "1200.00"),
        ("Hoodie", "1800.00"),
        ("T-shirt", "600.00"),
        ("Saree", "3500.00"),
        ("Blazer", "5500.00"),
    ],
    "Footwear": [
        ("Running shoes", "3000.00"),
        ("Leather sandals", "1400.00"),
        ("Formal shoes", "4200.00"),
        ("Sneakers", "2800.00"),
        ("Flip-flops", "400.00"),
        ("Hiking boots", "6500.00"),
    ],
    "Home & Kitchen": [
        ("Mixer grinder", "6000.00"),
        ("Juicer mixer", "6000.00"),
        ("Pressure cooker", "2400.00"),
        ("Non-stick pan", "1300.00"),
        ("Bedsheet set", "1900.00"),
        ("Table lamp", "1100.00"),
        ("Water bottle set", "700.00"),
    ],
    "Innerwear": [
        ("Cotton vest", "600.00"),
        ("Boxer briefs pack", "800.00"),
        ("Sports bra", "900.00"),
        ("Thermal set", "1500.00"),
        ("Socks pack", "450.00"),
    ],
    "Perishables": [
        ("Alphonso mangoes 1 kg", "900.00"),
        ("Organic honey", "550.00"),
        ("Dry fruit box", "1800.00"),
        ("Assorted sweets", "750.00"),
        ("Coffee beans", "650.00"),
        ("Green tea", "400.00"),
    ],
}

STAFF = [
    ("Wasim Khan", "warehouse1@example.com", Role.WAREHOUSE_AGENT),
    ("Farah Iyer", "finance1@example.com", Role.FINANCE_REVIEWER),
    ("Meera Nair", "manager1@example.com", Role.OPS_MANAGER),
]

DEMO_CUSTOMER = ("Asha Verma", "asha.verma@example.com")
FREQUENT_RETURNER = ("Rohan Mehta", "rohan.mehta@example.com")

# Order number, products, delivered this many days ago. What each one proves is in the plan.
DEMO_ORDERS: list[tuple[str, list[str], int]] = [
    ("ORD-DEMO-01", ["Cotton shirt"], 5),
    ("ORD-DEMO-02", ["Smartphone A52"], 11),
    ("ORD-DEMO-03", ["Wireless earbuds"], 10),
    ("ORD-DEMO-04", ["Cotton vest"], 3),
    ("ORD-DEMO-05", ["Denim jeans"], 30),
    ("ORD-DEMO-06", ["Denim jeans"], 31),
    ("ORD-DEMO-07", ["Rain jacket"], 5),
    ("ORD-DEMO-08", ["Laptop 14 inch"], 3),
    ("ORD-DEMO-09", ["Mixer grinder", "Juicer mixer"], 4),
    ("ORD-DEMO-10", ["Smartphone A52", "Cotton shirt"], 14),
]
FREQUENT_RETURNER_ORDER = ("ORD-DEMO-11", ["Running shoes"], 6)
PRIOR_RETURNS = 3  # with the next one, the 4th in 30 days, the customer is flagged

TABLES = (
    "ledger_entries, finance_approvals, refunds, inspections, return_photos, return_items, "
    "customer_flags, audit_log, returns, order_items, orders, products, customers, staff_users"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--if-empty", action="store_true", help="skip when data already exists")
    arguments = parser.parse_args()

    with session_scope() as session:
        if arguments.if_empty and session.scalar(select(func.count()).select_from(Customer)):
            print("Data already present; nothing to seed.")
            return
        seed(session)


def seed(session: Session) -> None:
    now = datetime.now(UTC)
    fake = Faker("en_IN")
    Faker.seed(SEED)
    rng = random.Random(SEED)  # noqa: S311 - repeatable synthetic data, not security

    reset(session)
    products = add_products(session)
    add_staff(session)
    demo_orders = add_demo_orders(session, products, now)
    customers = add_customers(session, fake, rng, CUSTOMERS - 2)
    add_random_orders(session, rng, customers, list(products.values()), now, ORDERS - demo_orders)
    print(
        f"Seeded {len(products)} products, {CUSTOMERS} customers, {ORDERS} orders "
        f"({demo_orders} demo), {len(STAFF)} staff users."
    )


def reset(session: Session) -> None:
    session.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    # Refund ids restart, so the gateway must forget old keys or it would replay old payments.
    if session.scalar(text("SELECT to_regclass('gateway.payments')")) is not None:
        session.execute(text("TRUNCATE gateway.payments RESTART IDENTITY"))


def add_products(session: Session) -> dict[str, Product]:
    categories = {category.name: category for category in session.scalars(select(Category))}
    products = {}
    for category_name, items in CATALOGUE.items():
        prefix = re.sub(r"[^A-Z]", "", category_name.upper())[:3]
        for number, (name, price) in enumerate(items, start=1):
            products[name] = Product(
                sku=f"{prefix}-{number:03d}",
                name=name,
                category_id=categories[category_name].category_id,
                price=Decimal(price),
            )
    session.add_all(products.values())
    session.flush()
    return products


def add_staff(session: Session) -> None:
    password_hash = hash_password(get_settings().demo_password)
    session.add_all(
        StaffUser(full_name=name, email=email, role=role, password_hash=password_hash)
        for name, email, role in STAFF
    )


def make_order(
    order_number: str, customer: Customer, products: list[Product], delivered_at: datetime
) -> Order:
    return Order(
        order_number=order_number,
        customer_id=customer.customer_id,
        payment_method="UPI",
        ordered_at=delivered_at - timedelta(days=3),
        delivered_at=delivered_at,
        total_amount=sum((product.price for product in products), Decimal("0")),
        items=[
            OrderItem(product_id=product.product_id, quantity=1, unit_price=product.price)
            for product in products
        ],
    )


def add_demo_orders(session: Session, products: dict[str, Product], now: datetime) -> int:
    asha = Customer(full_name=DEMO_CUSTOMER[0], email=DEMO_CUSTOMER[1])
    rohan = Customer(full_name=FREQUENT_RETURNER[0], email=FREQUENT_RETURNER[1])
    session.add_all([asha, rohan])
    session.flush()

    orders = [
        make_order(number, asha, [products[name] for name in names], now - timedelta(days=days))
        for number, names, days in DEMO_ORDERS
    ]
    number, names, days = FREQUENT_RETURNER_ORDER
    orders.append(
        make_order(number, rohan, [products[name] for name in names], now - timedelta(days=days))
    )
    prior = [
        make_order(f"{number}{suffix}", rohan, [products["T-shirt"]], now - timedelta(days=12))
        for suffix in "ABC"[:PRIOR_RETURNS]
    ]
    session.add_all(orders + prior)
    session.flush()
    add_prior_returns(session, prior, now)
    return len(orders) + len(prior)


def add_prior_returns(session: Session, orders: list[Order], now: datetime) -> None:
    """Three approved returns in the last 30 days, so the frequent returner's next one flags."""
    reason_id = session.scalar(
        select(ReasonCode.reason_id).where(ReasonCode.code == ReturnReason.CHANGED_MIND.name)
    )
    for days_ago, order in zip((6, 4, 2), orders, strict=True):
        requested_at = now - timedelta(days=days_ago)
        code = new_return_code()
        return_request = ReturnRequest(
            return_code=code,
            label_code=code,
            order_id=order.order_id,
            customer_id=order.customer_id,
            status=ReturnStatus.APPROVED,
            refund_method=RefundMethod.STORE_CREDIT,
            awaiting_finance=False,
            requested_at=requested_at,
            items=[
                ReturnItem(
                    order_item_id=item.order_item_id,
                    quantity=1,
                    reason_id=reason_id,
                    days_since_delivery=12 - days_ago,
                    is_eligible=True,
                    eligibility_reason="Within the 30-day return window.",
                )
                for item in order.items
            ],
        )
        session.add(return_request)
        session.flush()
        for old, new in (
            (None, ReturnStatus.REQUESTED),
            (ReturnStatus.REQUESTED, ReturnStatus.APPROVED),
        ):
            session.add(
                AuditLog(
                    return_id=return_request.return_id,
                    entity_type="RETURN",
                    entity_id=return_request.return_id,
                    action=STATUS_CHANGE,
                    old_status=old.name if old else None,
                    new_status=new.name,
                    actor_type="SYSTEM",
                    details={"actor": "seed"},
                    created_at=requested_at,
                )
            )


def add_customers(session: Session, fake: Faker, rng: random.Random, count: int) -> list[Customer]:
    customers = []
    for number in range(1, count + 1):
        first, last = fake.first_name(), fake.last_name()
        slug = re.sub(r"[^a-z]", "", f"{first}.{last}".lower().replace(".", "x"))
        customers.append(
            Customer(
                full_name=f"{first} {last}",
                email=f"{slug}{number}@example.com",
                phone=f"+91 9{rng.randint(100_000_000, 999_999_999)}",
            )
        )
    session.add_all(customers)
    session.flush()
    return customers


def add_random_orders(
    session: Session,
    rng: random.Random,
    customers: list[Customer],
    products: list[Product],
    now: datetime,
    count: int,
) -> None:
    orders = []
    for number in range(count):
        ordered_at = now - timedelta(days=rng.uniform(1, 120))
        delivered_at = ordered_at + timedelta(days=rng.randint(2, 6))
        lines = rng.sample(products, k=rng.choices((1, 2, 3), weights=(55, 30, 15))[0])
        quantities = [rng.choices((1, 2), weights=(85, 15))[0] for _ in lines]
        orders.append(
            Order(
                order_number=f"ORD-{100_001 + number}",
                customer_id=rng.choice(customers).customer_id,
                payment_method=rng.choice(PAYMENT_METHODS),
                ordered_at=ordered_at,
                delivered_at=delivered_at if delivered_at <= now else None,
                total_amount=sum(
                    (
                        product.price * quantity
                        for product, quantity in zip(lines, quantities, strict=True)
                    ),
                    Decimal("0"),
                ),
                items=[
                    OrderItem(
                        product_id=product.product_id, quantity=quantity, unit_price=product.price
                    )
                    for product, quantity in zip(lines, quantities, strict=True)
                ],
            )
        )
    session.add_all(orders)
    session.flush()


if __name__ == "__main__":
    main()
