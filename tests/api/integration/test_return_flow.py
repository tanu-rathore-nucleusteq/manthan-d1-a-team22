"""End to end through the API on the real PostgreSQL in DATABASE_URL; skipped when it is down.

Each test runs inside one outer transaction that is rolled back afterwards: the services' own
commits become savepoints, so they behave exactly as in production and nothing is left behind.
The gateway is a fake that, like the mock service, pays once per key and can fail on demand.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from returnright.api.deps import get_payment_gateway
from returnright.core.config import get_settings
from returnright.core.security import hash_password
from returnright.db.session import get_db, get_engine
from returnright.domain.enums import Role
from returnright.dtos.internal.payments import GatewayPaymentRequest, GatewayPaymentResult
from returnright.interfaces.payment_gateway import GatewayUnavailableError
from returnright.main import app
from returnright.models import (
    AuditLog,
    Category,
    Customer,
    CustomerFlag,
    Order,
    OrderItem,
    Product,
    ReturnRequest,
    StaffUser,
)

PASSWORD = "integration-pass-123"
PASSWORD_HASH = hash_password(PASSWORD)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class FakeGateway:
    def __init__(self) -> None:
        self.paid: dict[str, str] = {}
        self.calls = 0
        self.failures_left = 0

    def pay(self, request: GatewayPaymentRequest) -> GatewayPaymentResult:
        self.calls += 1
        if self.failures_left:
            self.failures_left -= 1
            raise GatewayUnavailableError("HTTP 502")
        replayed = request.idempotency_key in self.paid
        transaction_id = self.paid.setdefault(request.idempotency_key, f"gw_{len(self.paid) + 1}")
        return GatewayPaymentResult(transaction_id, "succeeded", replayed, 1.0)


class World:
    """Customers, orders and staff created inside the test transaction."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.categories = {category.name: category for category in db.scalars(select(Category))}

    def customer(self) -> Customer:
        customer = Customer(full_name="Test Customer", email=f"{uuid.uuid4().hex[:10]}@example.com")
        self.db.add(customer)
        self.db.flush()
        return customer

    def order(
        self, customer: Customer, delivered_days_ago: int, *lines: tuple[str, str, int]
    ) -> Order:
        """lines: (category, unit price, quantity)."""
        now = datetime.now(UTC)
        order = Order(
            order_number=f"IT-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer.customer_id,
            payment_method="UPI",
            ordered_at=now - timedelta(days=delivered_days_ago + 3),
            delivered_at=now - timedelta(days=delivered_days_ago),
            total_amount=sum(Decimal(price) * quantity for _, price, quantity in lines),
        )
        self.db.add(order)
        self.db.flush()
        for category, price, quantity in lines:
            product = Product(
                sku=f"IT-{uuid.uuid4().hex[:10]}",
                name=f"{category} item",
                category_id=self.categories[category].category_id,
                price=Decimal(price),
            )
            self.db.add(product)
            self.db.flush()
            self.db.add(
                OrderItem(
                    order_id=order.order_id,
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price=Decimal(price),
                )
            )
        self.db.flush()
        return order

    def order_item_ids(self, order: Order) -> list[int]:
        statement = (
            select(OrderItem.order_item_id)
            .where(OrderItem.order_id == order.order_id)
            .order_by(OrderItem.order_item_id)
        )
        return list(self.db.scalars(statement))

    def staff(self, role: Role) -> str:
        username = f"t{uuid.uuid4().hex[:10]}"
        self.db.add(
            StaffUser(
                full_name="Test Staff",
                email=f"{username}@example.com",
                role=role,
                password_hash=PASSWORD_HASH,
            )
        )
        self.db.flush()
        return username


@pytest.fixture
def db():
    try:
        connection = get_engine().connect()
    except OperationalError:
        pytest.skip("PostgreSQL is not reachable at DATABASE_URL")
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        autoflush=False,
    )
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def world(db) -> World:
    return World(db)


@pytest.fixture
def client(db, gateway, tmp_path):
    settings = get_settings().model_copy(update={"upload_dir": str(tmp_path)})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_payment_gateway] = lambda: gateway
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- helpers ---------------------------------------------------------------------------------


def create_return(client, order, email, order_item_ids, method="original_payment"):
    return client.post(
        "/api/v1/returns",
        json={
            "order_number": order.order_number,
            "email": email,
            "items": [
                {"order_item_id": item_id, "reason": "damaged"} for item_id in order_item_ids
            ],
            "refund_method": method,
        },
    )


def staff_headers(client, world, role: Role) -> dict[str, str]:
    username = world.staff(role)
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def returned_and_received(client, world, *lines, method="original_payment"):
    """A return created, shipped and received; returns (code, items, agent headers)."""
    customer = world.customer()
    order = world.order(customer, 5, *lines)
    created = create_return(client, order, customer.email, world.order_item_ids(order), method)
    assert created.status_code == 201, created.text
    code = created.json()["return_code"]
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)
    assert (
        client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=agent).status_code == 200
    )
    return code, created.json()["items"], agent


def inspect(client, code, agent, items, grade="A", decision="accept"):
    grades = [
        {"return_item_id": item["return_item_id"], "grade": grade, "decision": decision}
        for item in items
    ]
    return client.post(
        f"/api/v1/warehouse/returns/{code}/inspection", json={"items": grades}, headers=agent
    )


def ledger_for(client, finance, refund_ids) -> list[dict]:
    rows = []
    for refund_id in refund_ids:
        page = client.get(f"/api/v1/finance/ledger?refund_id={refund_id}", headers=finance).json()
        rows.extend(page["items"])
    return rows


# --- tests -----------------------------------------------------------------------------------


def test_grade_a_return_is_refunded_once_with_one_ledger_row(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    result = inspect(client, code, agent, items)

    assert result.status_code == 200, result.text
    assert result.json()["status"] == "refunded"
    assert result.json()["refund_total"] == "1500.00"
    assert gateway.calls == 1
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    refunds = client.get("/api/v1/finance/refunds?status=paid", headers=finance).json()["items"]
    refund = next(r for r in refunds if r["return_code"] == code)
    ledger = ledger_for(client, finance, [refund["refund_id"]])
    assert [(row["entry_type"], row["amount"]) for row in ledger] == [("refund", "1500.00")]


def test_timeline_lists_every_status_in_order(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items)

    detail = client.get(f"/api/v1/warehouse/returns/{code}", headers=agent).json()

    assert [event["status"] for event in detail["timeline"]] == [
        "requested",
        "approved",
        "in_transit",
        "received",
        "inspected",
        "refunded",
    ]


def test_grade_c_item_of_2000_refunds_1000(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "2000.00", 1))

    result = inspect(client, code, agent, items, grade="C").json()

    assert result["items"][0]["refund_amount"] == "1000.00"
    assert result["status"] == "refunded"


def test_two_items_of_6000_wait_for_finance_and_pay_only_after_approval(client, world, gateway):
    code, items, agent = returned_and_received(
        client, world, ("Home & Kitchen", "6000.00", 1), ("Home & Kitchen", "6000.00", 1)
    )

    inspected = inspect(client, code, agent, items).json()

    assert inspected["status"] == "inspected"
    assert inspected["needs_finance_approval"] is True
    assert gateway.calls == 0
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    queue = client.get("/api/v1/finance/approvals", headers=finance).json()["items"]
    assert any(entry["return_code"] == code for entry in queue)

    decided = client.post(
        f"/api/v1/finance/approvals/{code}/decision", json={"approve": True}, headers=finance
    )

    assert decided.status_code == 200, decided.text
    assert {r["status"] for r in decided.json()["refunds"]} == {"paid"}
    assert gateway.calls == 2
    again = client.post(
        f"/api/v1/finance/approvals/{code}/decision", json={"approve": True}, headers=finance
    )
    assert again.status_code == 409
    assert again.json()["code"] == "already_decided"


def test_finance_rejection_closes_the_return_without_paying(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Electronics", "12000.00", 1))
    inspect(client, code, agent, items)
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)

    decided = client.post(
        f"/api/v1/finance/approvals/{code}/decision",
        json={"approve": False, "comment": "Photo shows a different model"},
        headers=finance,
    )

    assert {r["status"] for r in decided.json()["refunds"]} == {"rejected"}
    detail = client.get(f"/api/v1/warehouse/returns/{code}", headers=agent).json()
    assert detail["status"] == "rejected"
    assert gateway.calls == 0


def test_failed_gateway_payment_is_retried_with_the_same_key_and_pays_once(client, world, gateway):
    gateway.failures_left = 1
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    inspected = inspect(client, code, agent, items).json()

    assert inspected["status"] == "inspected"
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    failed = client.get("/api/v1/finance/refunds?status=failed", headers=finance).json()["items"]
    refund_id = next(r["refund_id"] for r in failed if r["return_code"] == code)

    retry_headers = {**finance, "Idempotency-Key": "retry-click-0001"}
    paid = client.post(f"/api/v1/finance/refunds/{refund_id}/pay", headers=retry_headers)
    paid_again = client.post(f"/api/v1/finance/refunds/{refund_id}/pay", headers=retry_headers)

    assert paid.json()["status"] == paid_again.json()["status"] == "paid"
    assert gateway.calls == 2  # the failure and one successful payment
    assert len(gateway.paid) == 1
    assert len(ledger_for(client, finance, [refund_id])) == 1
    detail = client.get(f"/api/v1/warehouse/returns/{code}", headers=agent).json()
    assert detail["status"] == "refunded"


def test_store_credit_is_paid_without_calling_the_gateway(client, world, gateway):
    code, items, agent = returned_and_received(
        client, world, ("Footwear", "3000.00", 1), method="store_credit"
    )

    result = inspect(client, code, agent, items).json()

    assert result["status"] == "refunded"
    assert gateway.calls == 0
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    refunds = client.get("/api/v1/finance/refunds?status=paid", headers=finance).json()["items"]
    refund = next(r for r in refunds if r["return_code"] == code)
    ledger = ledger_for(client, finance, [refund["refund_id"]])
    assert [(row["method"], row["gateway_transaction_id"]) for row in ledger] == [
        ("store_credit", None)
    ]


def test_rejecting_every_item_rejects_the_return_with_no_refund(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    result = inspect(client, code, agent, items, decision="reject").json()

    assert result["status"] == "rejected"
    assert result["refund_total"] == "0.00"
    assert gateway.calls == 0


def test_partial_accept_refunds_only_the_accepted_item(client, world):
    code, items, agent = returned_and_received(
        client, world, ("Apparel", "1500.00", 1), ("Apparel", "900.00", 1)
    )
    grades = [
        {"return_item_id": items[0]["return_item_id"], "grade": "A", "decision": "accept"},
        {"return_item_id": items[1]["return_item_id"], "grade": "C", "decision": "reject"},
    ]

    result = client.post(
        f"/api/v1/warehouse/returns/{code}/inspection", json={"items": grades}, headers=agent
    ).json()

    assert result["status"] == "refunded"
    assert result["refund_total"] == "1500.00"


def test_double_submit_of_the_same_item_is_refused_with_409(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    item_ids = world.order_item_ids(order)

    first = create_return(client, order, customer.email, item_ids)
    second = create_return(client, order, customer.email, item_ids)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "duplicate_return"


def test_electronics_on_day_11_are_refused_with_422_and_the_reason(client, world):
    customer = world.customer()
    order = world.order(customer, 11, ("Electronics", "8000.00", 1))

    response = create_return(client, order, customer.email, world.order_item_ids(order))

    assert response.status_code == 422
    assert response.json()["code"] == "item_not_eligible"
    assert "10-day return window" in response.json()["message"]


def test_scanning_a_parcel_twice_answers_already_received(client, world):
    code, _items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    second_scan = client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=agent)

    assert second_scan.status_code == 409
    assert second_scan.json()["code"] == "already_received"


def test_label_scanned_before_shipping_moves_through_in_transit(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)

    received = client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=agent).json()

    assert received["status"] == "received"
    assert [event["status"] for event in received["timeline"]][-2:] == ["in_transit", "received"]


def test_inspection_must_grade_every_item(client, world):
    code, items, agent = returned_and_received(
        client, world, ("Apparel", "1500.00", 1), ("Apparel", "900.00", 1)
    )

    response = inspect(client, code, agent, items[:1])

    assert response.status_code == 422
    assert response.json()["code"] == "inspection_mismatch"


def test_shipping_twice_is_an_invalid_transition(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})

    again = client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})

    assert again.status_code == 409
    assert again.json()["code"] == "invalid_transition"


def test_fourth_return_in_30_days_flags_the_customer_and_the_third_does_not(client, world, db):
    customer = world.customer()
    for count in range(1, 5):
        order = world.order(customer, 5, ("Apparel", "500.00", 1))
        assert (
            create_return(client, order, customer.email, world.order_item_ids(order)).status_code
            == 201
        )
        db.refresh(customer)
        assert customer.is_flagged is (count == 4)
    flags = db.scalar(
        select(func.count())
        .select_from(CustomerFlag)
        .where(CustomerFlag.customer_id == customer.customer_id)
    )
    assert flags == 1


def test_wrong_email_cannot_read_a_return(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]

    own = client.get(f"/api/v1/returns/{code}", headers={"X-Customer-Email": customer.email})
    other = client.get(f"/api/v1/returns/{code}", headers={"X-Customer-Email": "x@example.com"})

    assert own.status_code == 200
    assert other.status_code == 404
    assert other.json()["code"] == "return_not_found"


def test_label_has_a_qr_code_and_the_warehouse_address(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]

    label = client.get(
        f"/api/v1/returns/{code}/label", headers={"X-Customer-Email": customer.email}
    ).json()

    assert label["qr_svg"].startswith("<svg")
    assert "Pithampur" in label["ship_to"]


def test_photo_upload_accepts_png_serves_it_and_refuses_other_files(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    created = create_return(client, order, customer.email, world.order_item_ids(order)).json()
    code, item_id = created["return_code"], created["items"][0]["return_item_id"]
    form = {"email": customer.email, "return_item_id": str(item_id)}

    uploaded = client.post(
        f"/api/v1/returns/{code}/photo", data=form, files={"photo": ("a.png", PNG, "image/png")}
    )
    refused = client.post(
        f"/api/v1/returns/{code}/photo",
        data=form,
        files={"photo": ("a.png", b"not really a picture", "image/png")},
    )

    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["content_type"] == "image/png"
    assert refused.status_code == 422
    assert refused.json()["code"] == "photo_rejected"
    detail = client.get(f"/api/v1/returns/{code}", headers={"X-Customer-Email": customer.email})
    assert detail.json()["items"][0]["photo_urls"] == [uploaded.json()["photo_url"]]


def test_every_status_change_writes_one_audit_row(client, world, db):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items)

    return_id = db.scalar(select(ReturnRequest.return_id).where(ReturnRequest.return_code == code))
    changes = db.scalars(
        select(AuditLog.new_status)
        .where(AuditLog.return_id == return_id, AuditLog.action == "STATUS_CHANGE")
        .order_by(AuditLog.audit_id)
    ).all()

    assert changes == ["REQUESTED", "APPROVED", "IN_TRANSIT", "RECEIVED", "INSPECTED", "REFUNDED"]


# --- dashboard and audit ---------------------------------------------------------------------


def dashboard(client, headers, **params) -> dict:
    response = client.get("/api/v1/dashboard", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def apparel(body: dict) -> dict:
    return next(row for row in body["return_rate_by_category"] if row["category"] == "Apparel")


def damaged(body: dict) -> int:
    return next((row["count"] for row in body["top_reasons"] if row["reason"] == "damaged"), 0)


def test_dashboard_counts_a_new_return_in_its_category_and_reason(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    before = dashboard(client, manager)
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))

    assert (
        create_return(client, order, customer.email, world.order_item_ids(order)).status_code == 201
    )
    after = dashboard(client, manager)

    assert apparel(after)["orders"] == apparel(before)["orders"] + 1
    assert apparel(after)["returns"] == apparel(before)["returns"] + 1
    assert apparel(after)["return_rate"] == round(
        apparel(after)["returns"] / apparel(after)["orders"], 4
    )
    assert damaged(after) == damaged(before) + 1


def test_dashboard_shows_the_flagged_customer_with_their_recent_returns(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    customer = world.customer()
    for _ in range(4):
        order = world.order(customer, 5, ("Apparel", "900.00", 1))
        create_return(client, order, customer.email, world.order_item_ids(order))

    flagged = dashboard(client, manager)["flagged_customers"]

    assert {
        "customer_id": customer.customer_id,
        "name": "Test Customer",
        "returns_last_30_days": 4,
    } in flagged


def test_dashboard_range_after_today_has_no_returns_and_no_cycle_time(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()

    body = dashboard(client, manager, date_from=tomorrow)

    assert all(row["returns"] == 0 for row in body["return_rate_by_category"])
    assert body["top_reasons"] == []
    assert body["average_cycle_time_hours"] is None


def test_dashboard_start_after_end_is_refused(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)

    response = client.get(
        "/api/v1/dashboard",
        params={"date_from": "2026-11-20", "date_to": "2026-11-01"},
        headers=manager,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_date_range"


def test_dashboard_is_for_operations_managers_only(client, world):
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)

    response = client.get("/api/v1/dashboard", headers=agent)

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_audit_trail_of_a_refunded_return_shows_each_change_and_the_payment(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items)
    manager = staff_headers(client, world, Role.OPS_MANAGER)

    entries = client.get(f"/api/v1/audit/returns/{code}", headers=manager).json()

    changes = [entry["to_status"] for entry in entries if entry["action"] == "status_change"]
    assert changes == ["requested", "approved", "in_transit", "received", "inspected", "refunded"]
    paid = [entry for entry in entries if entry["action"] == "paid"]
    assert len(paid) == 1
    assert paid[0]["entity"] == "refund"
    assert paid[0]["to_status"] == "paid"
    received = next(entry for entry in entries if entry["to_status"] == "received")
    assert received["actor_role"] == "warehouse_agent"


def test_audit_log_filters_by_entity_newest_first(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    return_id = client.get(f"/api/v1/audit/returns/{code}", headers=manager).json()[0]["entity_id"]

    page = client.get(
        "/api/v1/audit", params={"entity": "return", "entity_id": return_id}, headers=manager
    ).json()

    assert page["total"] == 4
    assert [entry["to_status"] for entry in page["items"]] == [
        "received",
        "in_transit",
        "approved",
        "requested",
    ]


def test_audit_trail_of_an_unknown_return_is_404(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)

    response = client.get("/api/v1/audit/returns/RR-NOPE0000", headers=manager)

    assert response.status_code == 404
    assert response.json()["code"] == "return_not_found"


# --- end-to-end catalogue: cases not covered above (docs/e2e-test-cases.md) ------------------


def refund_ids_for(client, finance, code, status) -> list[int]:
    page = client.get(f"/api/v1/finance/refunds?status={status}&size=100", headers=finance).json()
    return [r["refund_id"] for r in page["items"] if r["return_code"] == code]


def test_innerwear_item_is_refused_with_422_when_submitted(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Innerwear", "500.00", 1))

    response = create_return(client, order, customer.email, world.order_item_ids(order))

    assert response.status_code == 422
    assert response.json()["code"] == "item_not_eligible"
    assert "can't be returned" in response.json()["message"]


@pytest.mark.parametrize(
    ("days", "status_code"),
    [(30, 201), (31, 422)],
    ids=["day 30 is accepted", "day 31 is refused"],
)
def test_return_window_boundary_on_submit(client, world, days, status_code):
    customer = world.customer()
    order = world.order(customer, days, ("Apparel", "1500.00", 1))

    response = create_return(client, order, customer.email, world.order_item_ids(order))

    assert response.status_code == status_code, response.text
    if status_code == 422:
        assert "30-day return window ended" in response.json()["message"]


def test_mixed_basket_is_refused_with_the_reason_and_the_eligible_item_alone_succeeds(
    client, world
):
    customer = world.customer()
    order = world.order(customer, 14, ("Electronics", "8000.00", 1), ("Apparel", "1500.00", 1))
    electronics_id, apparel_id = world.order_item_ids(order)

    both = create_return(client, order, customer.email, [electronics_id, apparel_id])
    apparel_only = create_return(client, order, customer.email, [apparel_id])

    assert both.status_code == 422
    assert "Electronics item" in both.json()["message"]
    assert "10-day return window" in both.json()["message"]
    assert "Apparel item" not in both.json()["message"]
    assert apparel_only.status_code == 201, apparel_only.text
    assert len(apparel_only.json()["items"]) == 1


def test_returning_more_than_was_bought_is_refused(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "500.00", 1))
    (item_id,) = world.order_item_ids(order)

    response = client.post(
        "/api/v1/returns",
        json={
            "order_number": order.order_number,
            "email": customer.email,
            "items": [{"order_item_id": item_id, "quantity": 2, "reason": "size"}],
            "refund_method": "original_payment",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_return_request"


def test_grade_b_item_refunds_the_full_price(client, world):
    code, items, agent = returned_and_received(client, world, ("Footwear", "2000.00", 1))

    result = inspect(client, code, agent, items, grade="B").json()

    assert result["items"][0]["refund_amount"] == "2000.00"
    assert result["status"] == "refunded"


def test_refund_of_exactly_10000_is_paid_without_finance(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Home & Kitchen", "10000.00", 1))

    result = inspect(client, code, agent, items).json()

    assert result["needs_finance_approval"] is False
    assert result["status"] == "refunded"
    assert gateway.calls == 1


def test_refund_of_10000_01_waits_for_finance(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Home & Kitchen", "10000.01", 1))

    result = inspect(client, code, agent, items).json()

    assert result["needs_finance_approval"] is True
    assert result["status"] == "inspected"
    assert gateway.calls == 0


def test_inspecting_a_return_twice_is_refused_and_pays_once(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items)

    second = inspect(client, code, agent, items, grade="C")

    assert second.status_code == 409
    assert second.json()["code"] == "invalid_transition"
    assert "Already inspected" in second.json()["message"]
    assert gateway.calls == 1


def test_inspection_before_the_parcel_is_received_is_an_invalid_transition(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    created = create_return(client, order, customer.email, world.order_item_ids(order)).json()
    code = created["return_code"]
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)

    response = inspect(client, code, agent, created["items"])

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


def test_paying_a_refund_that_waits_for_finance_is_refused(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Electronics", "12000.00", 1))
    inspect(client, code, agent, items)
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    (refund_id,) = refund_ids_for(client, finance, code, "pending_approval")

    response = client.post(
        f"/api/v1/finance/refunds/{refund_id}/pay",
        headers={**finance, "Idempotency-Key": "early-pay-0001"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "refund_not_payable"
    assert gateway.calls == 0


def test_double_click_on_pay_for_a_paid_refund_pays_once(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items)
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    (refund_id,) = refund_ids_for(client, finance, code, "paid")
    headers = {**finance, "Idempotency-Key": "double-click-0001"}

    first = client.post(f"/api/v1/finance/refunds/{refund_id}/pay", headers=headers)
    second = client.post(f"/api/v1/finance/refunds/{refund_id}/pay", headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "paid"
    assert gateway.calls == 1
    assert len(ledger_for(client, finance, [refund_id])) == 1


def test_ledger_matches_every_paid_refund_after_mixed_flows(client, world, db):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items, grade="C")
    code, items, agent = returned_and_received(
        client, world, ("Footwear", "3000.00", 1), method="store_credit"
    )
    inspect(client, code, agent, items)

    mismatches = db.scalar(text("SELECT count(*) FROM returnright.v_ledger_check"))

    assert mismatches == 0


def test_customer_timeline_is_ordered_and_visible_only_to_the_owner(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})

    own = client.get(
        f"/api/v1/returns/{code}/timeline", headers={"X-Customer-Email": customer.email}
    )
    other = client.get(
        f"/api/v1/returns/{code}/timeline", headers={"X-Customer-Email": "x@example.com"}
    )

    assert own.status_code == 200
    assert [event["status"] for event in own.json()] == ["requested", "approved", "in_transit"]
    assert other.status_code == 404


def test_wrong_email_cannot_mark_a_return_shipped(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]

    response = client.post(f"/api/v1/returns/{code}/ship", json={"email": "x@example.com"})

    assert response.status_code == 404
    detail = client.get(f"/api/v1/returns/{code}", headers={"X-Customer-Email": customer.email})
    assert detail.json()["status"] == "approved"


def test_warehouse_queue_moves_a_return_from_in_transit_to_received(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)

    def queue(status: str) -> set[str]:
        page = client.get(f"/api/v1/warehouse/returns?status={status}&size=100", headers=agent)
        return {row["return_code"] for row in page.json()["items"]}

    assert code in queue("in_transit")
    client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=agent)
    assert code not in queue("in_transit")
    assert code in queue("received")


def test_each_role_is_refused_on_the_other_roles_actions(client, world):
    code, items, _agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)

    finance_inspects = inspect(client, code, finance, items)
    agent_reads_approvals = client.get("/api/v1/finance/approvals", headers=agent)

    assert finance_inspects.status_code == 403
    assert agent_reads_approvals.status_code == 403


def test_flagged_customer_can_still_make_a_fifth_return(client, world, db):
    customer = world.customer()
    statuses = []
    for _ in range(5):
        order = world.order(customer, 5, ("Apparel", "500.00", 1))
        statuses.append(
            create_return(client, order, customer.email, world.order_item_ids(order)).status_code
        )

    db.refresh(customer)
    assert statuses == [201] * 5
    assert customer.is_flagged is True
    flags = db.scalar(
        select(func.count())
        .select_from(CustomerFlag)
        .where(CustomerFlag.customer_id == customer.customer_id)
    )
    assert flags == 1


def test_photo_larger_than_the_limit_is_refused_with_413(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    created = create_return(client, order, customer.email, world.order_item_ids(order)).json()
    too_big = PNG + b"\x00" * (get_settings().upload_max_mb * 1024 * 1024)

    response = client.post(
        f"/api/v1/returns/{created['return_code']}/photo",
        data={
            "email": customer.email,
            "return_item_id": str(created["items"][0]["return_item_id"]),
        },
        files={"photo": ("big.png", too_big, "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "photo_too_large"


def test_finance_can_open_a_return_before_deciding_but_cannot_receive_it(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    code = create_return(client, order, customer.email, world.order_item_ids(order)).json()[
        "return_code"
    ]
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)

    detail = client.get(f"/api/v1/warehouse/returns/{code}", headers=finance)
    receive = client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=finance)

    assert detail.status_code == 200
    assert detail.json()["customer_name"] == "Test Customer"
    assert receive.status_code == 403
