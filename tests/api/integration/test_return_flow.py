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
from returnright.repositories.return_repository import ReturnRepository

PASSWORD = "integration-pass-123"
PASSWORD_HASH = hash_password(PASSWORD)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class FakeGateway:
    def __init__(self) -> None:
        self.paid: dict[str, str] = {}
        self.calls = 0
        self.failures_left = 0
        self.decline = False  # the bank answers "failed" instead of paying
        self.on_pay = None  # called while the payment is in flight, e.g. a parallel request

    def pay(self, request: GatewayPaymentRequest) -> GatewayPaymentResult:
        self.calls += 1
        if self.on_pay:
            self.on_pay(request)
        if self.failures_left:
            self.failures_left -= 1
            raise GatewayUnavailableError("HTTP 502")
        if self.decline:
            return GatewayPaymentResult(f"gw_declined_{self.calls}", "failed", False, 1.0)
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


# --- staff accounts --------------------------------------------------------------------------


def new_staff(client, manager, **overrides):
    body = {
        "full_name": "Meera Iyer",
        "email": f"m{uuid.uuid4().hex[:8]}@example.com",
        "role": "warehouse_agent",
        "password": "temporary-pass-42",
    } | overrides
    return client.post("/api/v1/staff", json=body, headers=manager)


def test_manager_adds_a_warehouse_agent_who_can_then_sign_in(client, world, db):
    manager = staff_headers(client, world, Role.OPS_MANAGER)

    created = new_staff(client, manager)

    assert created.status_code == 201, created.text
    member = created.json()
    assert member["role"] == "warehouse_agent"
    assert member["is_active"] is True
    assert "password" not in member and "password_hash" not in member
    login = client.post(
        "/api/v1/auth/login",
        json={"username": member["username"], "password": "temporary-pass-42"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "warehouse_agent"
    audit = db.scalars(
        select(AuditLog.action).where(
            AuditLog.entity_type == "STAFF", AuditLog.entity_id == member["user_id"]
        )
    ).all()
    assert audit == ["CREATED"]


def test_email_or_username_already_used_is_refused_with_409(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    first = new_staff(client, manager).json()

    same_email = new_staff(client, manager, email=first["email"].upper())
    same_username = new_staff(client, manager, email=f"{first['username']}@other.example.com")

    assert same_email.status_code == 409
    assert same_email.json()["code"] == "staff_login_taken"
    assert same_username.status_code == 409


@pytest.mark.parametrize("password", ["short1", "onlyletters", "1234567890"])
def test_weak_temporary_password_is_refused(client, world, password):
    manager = staff_headers(client, world, Role.OPS_MANAGER)

    response = new_staff(client, manager, password=password)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "password"


def test_only_the_operations_manager_can_add_staff(client, world):
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)

    assert new_staff(client, finance, role="finance_reviewer").status_code == 403
    assert client.post("/api/v1/staff", json={}).status_code == 401


def test_switched_off_account_cannot_sign_in_and_can_be_switched_back_on(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    member = new_staff(client, manager).json()
    credentials = {"username": member["username"], "password": "temporary-pass-42"}

    off = client.patch(
        f"/api/v1/staff/{member['user_id']}", json={"is_active": False}, headers=manager
    )
    refused = client.post("/api/v1/auth/login", json=credentials)
    on = client.patch(
        f"/api/v1/staff/{member['user_id']}", json={"is_active": True}, headers=manager
    )

    assert off.json()["is_active"] is False
    assert refused.status_code == 401
    assert on.json()["is_active"] is True
    assert client.post("/api/v1/auth/login", json=credentials).status_code == 200


def test_manager_cannot_switch_off_their_own_account(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    me = client.get("/api/v1/auth/me", headers=manager).json()

    response = client.patch(
        f"/api/v1/staff/{me['user_id']}", json={"is_active": False}, headers=manager
    )

    assert response.status_code == 409
    assert response.json()["code"] == "cannot_deactivate_self"


def test_team_list_shows_every_account_without_passwords(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    member = new_staff(client, manager).json()

    team = client.get("/api/v1/staff", headers=manager).json()

    assert member in team
    assert all("password_hash" not in row for row in team)


# --- coverage gaps: races, gateway outcomes, validation edges, dashboard parts ---------------


def race_before_next_commit(db, monkeypatch, sql: str, params: dict) -> None:
    """Run a competing write just before the service's next commit, as if another request
    committed between this request reading the row and writing it back."""
    real_commit = db.commit

    def racing_commit():
        monkeypatch.setattr(db, "commit", real_commit)
        db.execute(text(sql), params)
        real_commit()

    monkeypatch.setattr(db, "commit", racing_commit)


def return_id_of(db, code: str) -> int:
    return db.scalar(select(ReturnRequest.return_id).where(ReturnRequest.return_code == code))


def mark_paid_by_a_parallel_request(db):
    def on_pay(request: GatewayPaymentRequest) -> None:
        db.execute(
            text(
                "UPDATE returnright.refunds SET status = 'PAID', paid_at = now(), "
                "gateway_reference = 'gw_parallel' WHERE refund_id = :refund_id"
            ),
            {"refund_id": request.refund_id},
        )

    return on_pay


def customer_return(client, world, *lines, delivered_days_ago=5):
    """A created return; returns (customer, code, items)."""
    customer = world.customer()
    order = world.order(customer, delivered_days_ago, *lines)
    created = create_return(client, order, customer.email, world.order_item_ids(order))
    assert created.status_code == 201, created.text
    return customer, created.json()["return_code"], created.json()["items"]


def upload(client, code, email, return_item_id, data=PNG):
    return client.post(
        f"/api/v1/returns/{code}/photo",
        data={"email": email, "return_item_id": str(return_item_id)},
        files={"photo": ("item.png", data, "image/png")},
    )


# Races: the second of two simultaneous requests is stopped by the database.


def test_same_item_submitted_twice_at_the_same_moment_is_stopped_by_the_database(
    client, world, monkeypatch
):
    # Both requests pass the "already returned?" check before either one has saved.
    monkeypatch.setattr(ReturnRepository, "order_items_already_returned", lambda self, ids: set())
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    item_ids = world.order_item_ids(order)

    first = create_return(client, order, customer.email, item_ids)
    second = create_return(client, order, customer.email, item_ids)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "duplicate_return"


def test_two_reviewers_deciding_at_the_same_moment_pay_once(
    client, world, db, gateway, monkeypatch
):
    code, items, agent = returned_and_received(client, world, ("Electronics", "12000.00", 1))
    inspect(client, code, agent, items)
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    other_reviewer = db.scalar(
        select(StaffUser.staff_id).where(
            StaffUser.email == f"{world.staff(Role.FINANCE_REVIEWER)}@example.com"
        )
    )
    race_before_next_commit(
        db,
        monkeypatch,
        "INSERT INTO returnright.finance_approvals (return_id, reviewer_id, decision) "
        "VALUES (:return_id, :reviewer_id, 'APPROVED')",
        {"return_id": return_id_of(db, code), "reviewer_id": other_reviewer},
    )

    response = client.post(
        f"/api/v1/finance/approvals/{code}/decision", json={"approve": True}, headers=finance
    )

    assert response.status_code == 409
    assert response.json()["code"] == "already_decided"
    assert gateway.calls == 0


def test_two_agents_inspecting_at_the_same_moment_only_one_wins(
    client, world, db, gateway, monkeypatch
):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    race_before_next_commit(
        db,
        monkeypatch,
        "UPDATE returnright.returns SET version = version + 1 WHERE return_id = :return_id",
        {"return_id": return_id_of(db, code)},
    )

    response = inspect(client, code, agent, items)

    assert response.status_code == 409
    assert response.json()["code"] == "concurrent_update"
    assert gateway.calls == 0
    detail = client.get(f"/api/v1/warehouse/returns/{code}", headers=agent).json()
    assert detail["status"] == "received"


def test_refund_settled_by_a_parallel_request_is_not_recorded_twice(client, world, db, gateway):
    gateway.on_pay = mark_paid_by_a_parallel_request(db)
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    inspect(client, code, agent, items)

    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    (refund_id,) = refund_ids_for(client, finance, code, "paid")
    refund = client.get(f"/api/v1/finance/refunds/{refund_id}", headers=finance).json()
    assert refund["gateway_transaction_id"] == "gw_parallel"  # the first finisher's payment
    assert ledger_for(client, finance, [refund_id]) == []  # this request added no second row


def test_gateway_error_after_a_parallel_request_paid_keeps_the_refund_paid(
    client, world, db, gateway
):
    gateway.on_pay = mark_paid_by_a_parallel_request(db)
    gateway.failures_left = 1
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    inspect(client, code, agent, items)

    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    assert len(refund_ids_for(client, finance, code, "paid")) == 1
    assert refund_ids_for(client, finance, code, "failed") == []


# Gateway outcomes and money paths.


def test_declined_payment_is_failed_and_a_later_retry_pays(client, world, gateway):
    gateway.decline = True
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    inspected = inspect(client, code, agent, items).json()

    assert inspected["status"] == "inspected"
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    (refund_id,) = refund_ids_for(client, finance, code, "failed")
    gateway.decline = False
    retried = client.post(
        f"/api/v1/finance/refunds/{refund_id}/pay",
        headers={**finance, "Idempotency-Key": "after-decline-0001"},
    )
    assert retried.json()["status"] == "paid"
    detail = client.get(f"/api/v1/warehouse/returns/{code}", headers=agent).json()
    assert detail["status"] == "refunded"


def test_paying_a_refund_that_finance_rejected_is_refused(client, world, gateway):
    code, items, agent = returned_and_received(client, world, ("Electronics", "12000.00", 1))
    inspect(client, code, agent, items)
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)
    client.post(
        f"/api/v1/finance/approvals/{code}/decision",
        json={"approve": False, "comment": "Damage not shown in photos"},
        headers=finance,
    )
    (refund_id,) = refund_ids_for(client, finance, code, "rejected")

    response = client.post(
        f"/api/v1/finance/refunds/{refund_id}/pay",
        headers={**finance, "Idempotency-Key": "pay-rejected-0001"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "refund_not_payable"
    assert gateway.calls == 0


def test_deciding_on_a_return_that_does_not_wait_for_finance_is_refused(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    inspect(client, code, agent, items)
    finance = staff_headers(client, world, Role.FINANCE_REVIEWER)

    response = client.post(
        f"/api/v1/finance/approvals/{code}/decision", json={"approve": True}, headers=finance
    )

    assert response.status_code == 409
    assert response.json()["code"] == "no_pending_approval"


@pytest.mark.parametrize(
    ("method", "path", "role", "body"),
    [
        ("get", "/api/v1/finance/refunds/999999", Role.FINANCE_REVIEWER, None),
        ("post", "/api/v1/finance/refunds/999999/pay", Role.FINANCE_REVIEWER, None),
        (
            "post",
            "/api/v1/finance/approvals/RR-NOPE0000/decision",
            Role.FINANCE_REVIEWER,
            {"approve": True},
        ),
        (
            "post",
            "/api/v1/warehouse/returns/RR-NOPE0000/inspection",
            Role.WAREHOUSE_AGENT,
            {"items": [{"return_item_id": 1, "grade": "A", "decision": "accept"}]},
        ),
    ],
    ids=["refund detail", "refund pay", "approval decision", "inspection"],
)
def test_unknown_refund_or_return_is_404(client, world, method, path, role, body):
    headers = {**staff_headers(client, world, role), "Idempotency-Key": "unknown-id-0001"}

    response = getattr(client, method)(path, headers=headers, **({"json": body} if body else {}))

    assert response.status_code == 404
    assert response.json()["code"] in {"refund_not_found", "return_not_found"}


# Request validation the earlier cases do not reach.


def test_creating_a_return_with_the_wrong_email_is_404(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))

    response = create_return(client, order, "someone.else@example.com", world.order_item_ids(order))

    assert response.status_code == 404
    assert response.json()["code"] == "order_not_found"


def test_the_same_item_listed_twice_in_one_request_is_refused(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    (item_id,) = world.order_item_ids(order)

    response = create_return(client, order, customer.email, [item_id, item_id])

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_return_request"
    assert "only be listed once" in response.json()["message"]


def test_an_item_from_another_order_is_refused(client, world):
    customer = world.customer()
    order = world.order(customer, 5, ("Apparel", "1500.00", 1))
    other = world.order(customer, 5, ("Apparel", "900.00", 1))

    response = create_return(client, order, customer.email, world.order_item_ids(other))

    assert response.status_code == 422
    assert "not part of this order" in response.json()["message"]


def test_label_of_a_rejected_return_is_unavailable(client, world):
    customer, code, items = customer_return(client, world, ("Apparel", "1500.00", 1))
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)
    client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=agent)
    inspect(client, code, agent, items, decision="reject")

    response = client.get(
        f"/api/v1/returns/{code}/label", headers={"X-Customer-Email": customer.email}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "label_unavailable"


def test_photo_after_the_warehouse_received_the_parcel_is_refused(client, world):
    customer, code, items = customer_return(client, world, ("Apparel", "1500.00", 1))
    client.post(f"/api/v1/returns/{code}/ship", json={"email": customer.email})
    agent = staff_headers(client, world, Role.WAREHOUSE_AGENT)
    client.post(f"/api/v1/warehouse/returns/{code}/receive", headers=agent)

    response = upload(client, code, customer.email, items[0]["return_item_id"])

    assert response.status_code == 422
    assert "before the warehouse receives" in response.json()["message"]


def test_photo_for_an_item_outside_the_return_is_refused(client, world):
    customer, code, _items = customer_return(client, world, ("Apparel", "1500.00", 1))

    response = upload(client, code, customer.email, 999999)

    assert response.status_code == 422
    assert "not part of this return" in response.json()["message"]


def test_sixth_photo_of_one_item_is_refused(client, world):
    customer, code, items = customer_return(client, world, ("Apparel", "1500.00", 1))
    item_id = items[0]["return_item_id"]
    limit = get_settings().photos_per_item_max

    accepted = [upload(client, code, customer.email, item_id).status_code for _ in range(limit)]
    extra = upload(client, code, customer.email, item_id)

    assert accepted == [201] * limit
    assert extra.status_code == 422
    assert f"at most {limit} photos" in extra.json()["message"]


def test_inspection_grading_one_item_twice_is_refused(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))

    response = inspect(client, code, agent, items + items)

    assert response.status_code == 422
    assert "only be graded once" in response.json()["message"]


def test_inspection_of_an_item_outside_the_return_is_refused(client, world):
    code, items, agent = returned_and_received(client, world, ("Apparel", "1500.00", 1))
    grades = [
        {"return_item_id": items[0]["return_item_id"], "grade": "A", "decision": "accept"},
        {"return_item_id": 999999, "grade": "A", "decision": "accept"},
    ]

    response = client.post(
        f"/api/v1/warehouse/returns/{code}/inspection", json={"items": grades}, headers=agent
    )

    assert response.status_code == 422
    assert "not part of this return" in response.json()["message"]


# The three dashboard endpoints that each read one part.


def test_return_rates_endpoint_counts_todays_return_and_sorts_highest_first(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    today = datetime.now(UTC).date().isoformat()
    customer_return(client, world, ("Apparel", "1500.00", 1))

    rates = client.get(
        f"/api/v1/dashboard/return-rates?date_from={today}&date_to={today}", headers=manager
    ).json()

    apparel_rate = next(rate for rate in rates if rate["category"] == "Apparel")
    assert apparel_rate["returns"] >= 1
    assert [rate["return_rate"] for rate in rates] == sorted(
        (rate["return_rate"] for rate in rates), reverse=True
    )


def test_top_reasons_endpoint_respects_the_limit_most_common_first(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    customer_return(client, world, ("Apparel", "1500.00", 1))

    reasons = client.get("/api/v1/dashboard/top-reasons?limit=2", headers=manager).json()

    assert 1 <= len(reasons) <= 2
    assert [reason["count"] for reason in reasons] == sorted(
        (reason["count"] for reason in reasons), reverse=True
    )


def test_flagged_customers_endpoint_lists_a_customer_with_four_returns(client, world):
    manager = staff_headers(client, world, Role.OPS_MANAGER)
    customer = world.customer()
    for _ in range(4):
        order = world.order(customer, 5, ("Apparel", "500.00", 1))
        create_return(client, order, customer.email, world.order_item_ids(order))

    flagged = client.get("/api/v1/dashboard/flagged-customers", headers=manager).json()

    entry = next(row for row in flagged if row["customer_id"] == customer.customer_id)
    assert entry["returns_last_30_days"] == 4
