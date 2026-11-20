"""Past returns for the seed, so the manager dashboard has history on the first run. Most are
refunded (grades A, B and C; original payment and store credit; finance-approved above the
threshold), some are rejected at inspection, and a few customers return often enough to be
flagged. Every row follows the live rules: refund amounts from the refund policy, one ledger row
per paid refund, one audit row per status change. Only closed returns are added, so the
warehouse and finance queues stay clear for the demo.
"""

import random
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from returnright.domain.customer_flags import check_frequent_returner
from returnright.domain.enums import (
    Grade,
    ItemDecision,
    LedgerEntryType,
    RefundMethod,
    RefundStatus,
    ReturnReason,
    ReturnStatus,
    Role,
)
from returnright.domain.refund_policy import (
    item_refund_amount,
    refund_percent,
    requires_finance_approval,
)
from returnright.models import (
    AuditLog,
    Customer,
    CustomerFlag,
    FinanceApproval,
    Inspection,
    LedgerEntry,
    Order,
    OrderItem,
    ReasonCode,
    Refund,
    ReturnItem,
    ReturnRequest,
    StaffUser,
)
from returnright.models.audit_log import STATUS_CHANGE
from returnright.models.refund import APPROVED
from returnright.utils.ids import new_return_code

# Chance that an item in the category is returned; never-returnable categories are absent.
RETURN_RATE = {"Apparel": 0.16, "Footwear": 0.13, "Electronics": 0.08, "Home & Kitchen": 0.06}
WINDOW_DAYS = {"Electronics": 10}
STANDARD_WINDOW_DAYS = 30

R = ReturnReason
REASON_WEIGHTS = {
    "Apparel": {R.SIZE: 45, R.QUALITY: 15, R.CHANGED_MIND: 15, R.NOT_AS_DESCRIBED: 12,
                R.DAMAGED: 5, R.WRONG_ITEM: 5, R.OTHER: 3},
    "Footwear": {R.SIZE: 50, R.QUALITY: 15, R.CHANGED_MIND: 12, R.NOT_AS_DESCRIBED: 10,
                 R.DAMAGED: 6, R.WRONG_ITEM: 4, R.OTHER: 3},
    "Electronics": {R.DAMAGED: 35, R.NOT_AS_DESCRIBED: 25, R.QUALITY: 20, R.WRONG_ITEM: 10,
                    R.CHANGED_MIND: 7, R.OTHER: 3},
    "Home & Kitchen": {R.DAMAGED: 40, R.QUALITY: 20, R.NOT_AS_DESCRIBED: 15, R.WRONG_ITEM: 10,
                       R.CHANGED_MIND: 10, R.OTHER: 5},
}  # fmt: skip
GRADE_WEIGHTS = {Grade.A: 55, Grade.B: 30, Grade.C: 15}
REJECTED_SHARE = 0.12
STORE_CREDIT_SHARE = 0.3

# Customers given several recent orders that they all return, so the dashboard shows flags.
FREQUENT_RETURNERS = 3
ORDERS_EACH = 5

# Where each status change falls between the request (0) and the close (1).
REFUNDED_STEPS = (
    (None, ReturnStatus.REQUESTED, 0.0),
    (ReturnStatus.REQUESTED, ReturnStatus.APPROVED, 0.0),
    (ReturnStatus.APPROVED, ReturnStatus.IN_TRANSIT, 0.15),
    (ReturnStatus.IN_TRANSIT, ReturnStatus.RECEIVED, 0.6),
    (ReturnStatus.RECEIVED, ReturnStatus.INSPECTED, 0.8),
    (ReturnStatus.INSPECTED, ReturnStatus.REFUNDED, 1.0),
)
REJECTED_STEPS = (*REFUNDED_STEPS[:4], (ReturnStatus.RECEIVED, ReturnStatus.REJECTED, 1.0))


def add_history(
    session: Session,
    rng: random.Random,
    orders: list[Order],
    category_of: dict[int, str],
    now: datetime,
) -> int:
    """Adds the past returns and flags; returns how many returns were added."""
    staff = {user.role: user.staff_id for user in session.scalars(select(StaffUser))}
    reasons = {row.code: row.reason_id for row in session.scalars(select(ReasonCode))}
    frequent = _make_frequent_returners(rng, orders, category_of, now)

    added: list[ReturnRequest] = []
    for order in orders:
        items = [
            item
            for item in order.items
            if category_of[item.product_id] in RETURN_RATE
            and (
                order.customer_id in frequent
                or rng.random() < RETURN_RATE[category_of[item.product_id]]
            )
        ]
        timing = _timing(rng, order, items, category_of, now)
        if timing is None:
            continue
        requested_at, closed_at = timing
        return_request = ReturnRequest(
            return_code=(code := new_return_code()),
            label_code=code,
            order_id=order.order_id,
            customer_id=order.customer_id,
            status=(
                ReturnStatus.REJECTED if rng.random() < REJECTED_SHARE else ReturnStatus.REFUNDED
            ),
            refund_method=(
                RefundMethod.STORE_CREDIT
                if rng.random() < STORE_CREDIT_SHARE
                else RefundMethod.ORIGINAL_PAYMENT
            ),
            awaiting_finance=False,
            requested_at=requested_at,
            closed_at=closed_at,
            items=[
                ReturnItem(
                    order_item_id=item.order_item_id,
                    quantity=item.quantity,
                    reason_id=reasons[_reason(rng, category_of[item.product_id]).name],
                    days_since_delivery=(requested_at.date() - order.delivered_at.date()).days,
                    is_eligible=True,
                    eligibility_reason="Within the return window.",
                )
                for item in items
            ],
        )
        session.add(return_request)
        session.flush()
        _close(session, rng, return_request, items, staff)
        added.append(return_request)

    _flag_frequent_returners(session, added, now)
    return len(added)


def _make_frequent_returners(
    rng: random.Random, orders: list[Order], category_of: dict[int, str], now: datetime
) -> set[int]:
    """Moves recent orders to a few customers; all of those orders get returned."""
    recent = [
        order
        for order in orders
        if order.delivered_at is not None
        and now - timedelta(days=25) <= order.delivered_at <= now - timedelta(days=5)
        and any(category_of[item.product_id] in RETURN_RATE for item in order.items)
    ]
    chosen = rng.sample(recent, FREQUENT_RETURNERS * ORDERS_EACH)
    customers = rng.sample(sorted({order.customer_id for order in orders}), FREQUENT_RETURNERS)
    for number, order in enumerate(chosen):
        order.customer_id = customers[number % FREQUENT_RETURNERS]
    return set(customers)


def _timing(
    rng: random.Random,
    order: Order,
    items: list[OrderItem],
    category_of: dict[int, str],
    now: datetime,
) -> tuple[datetime, datetime] | None:
    """A request inside every item's window and a close before now, or None if neither fits."""
    if not items or order.delivered_at is None:
        return None
    window = min(
        WINDOW_DAYS.get(category_of[item.product_id], STANDARD_WINDOW_DAYS) for item in items
    )
    latest = min(order.delivered_at + timedelta(days=window), now - timedelta(days=2))
    if latest <= order.delivered_at:
        return None
    requested_at = order.delivered_at + (latest - order.delivered_at) * rng.uniform(0.05, 1)
    cycle = min(timedelta(hours=rng.uniform(30, 160)), (now - requested_at) * 0.9)
    return requested_at, requested_at + cycle


def _reason(rng: random.Random, category: str) -> ReturnReason:
    weights = REASON_WEIGHTS[category]
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _close(
    session: Session,
    rng: random.Random,
    return_request: ReturnRequest,
    order_items: list[OrderItem],
    staff: dict[Role, int],
) -> None:
    """Inspection, refunds, ledger, finance approval and audit rows of a closed return."""
    requested_at, closed_at = return_request.requested_at, return_request.closed_at
    cycle = closed_at - requested_at
    inspected_at = requested_at + cycle * 0.8
    refunded = return_request.status is ReturnStatus.REFUNDED
    decision = ItemDecision.ACCEPT if refunded else ItemDecision.REJECT

    amounts: list[tuple[ReturnItem, Decimal]] = []
    for item, order_item in zip(return_request.items, order_items, strict=True):
        grade = rng.choices(list(GRADE_WEIGHTS), weights=list(GRADE_WEIGHTS.values()))[0]
        session.add(
            Inspection(
                return_item_id=item.return_item_id,
                agent_id=staff[Role.WAREHOUSE_AGENT],
                grade=grade,
                decision=decision,
                refund_percent=refund_percent(grade, decision),
                inspected_at=inspected_at,
            )
        )
        if refunded:
            amount = item_refund_amount(order_item.unit_price, item.quantity, grade, decision)
            amounts.append((item, amount))

    needs_approval = requires_finance_approval(sum(amount for _, amount in amounts))
    if needs_approval:
        session.add(
            FinanceApproval(
                return_id=return_request.return_id,
                reviewer_id=staff[Role.FINANCE_REVIEWER],
                decision=APPROVED,
                decided_at=requested_at + cycle * 0.9,
            )
        )
    method = return_request.refund_method
    for item, amount in amounts:
        reference = (
            f"seed-{item.return_item_id}" if method is RefundMethod.ORIGINAL_PAYMENT else None
        )
        refund = Refund(
            return_item_id=item.return_item_id,
            amount=amount,
            method=method,
            requires_approval=needs_approval,
            status=RefundStatus.PAID,
            idempotency_key=f"refund-{item.return_item_id}",
            gateway_reference=reference,
            attempt_count=0 if reference is None else 1,
            created_at=inspected_at,
            paid_at=closed_at,
        )
        session.add(refund)
        session.flush()
        session.add(
            LedgerEntry(
                refund_id=refund.refund_id,
                customer_id=return_request.customer_id,
                entry_type=LedgerEntryType.REFUND,
                amount=amount,
                method=method,
                gateway_reference=reference,
                created_at=closed_at,
            )
        )

    for old, new, share in REFUNDED_STEPS if refunded else REJECTED_STEPS:
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
                created_at=requested_at + cycle * share,
            )
        )


def _flag_frequent_returners(session: Session, returns: list[ReturnRequest], now: datetime) -> None:
    """Flags every customer the live rule would flag: more than 3 returns in 30 days."""
    by_customer: dict[int, list[ReturnRequest]] = defaultdict(list)
    for return_request in returns:
        by_customer[return_request.customer_id].append(return_request)
    flagged = []
    for customer_id, customer_returns in by_customer.items():
        check = check_frequent_returner(
            (item.requested_at.date() for item in customer_returns), now.date()
        )
        if not check.flagged:
            continue
        trigger = sorted(customer_returns, key=lambda item: item.requested_at)[-1]
        session.add(
            CustomerFlag(
                customer_id=customer_id,
                trigger_return_id=trigger.return_id,
                returns_in_30d=check.returns_in_window,
                flagged_at=trigger.requested_at,
            )
        )
        flagged.append(customer_id)
    if flagged:
        session.execute(
            update(Customer).where(Customer.customer_id.in_(flagged)).values(is_flagged=True)
        )
