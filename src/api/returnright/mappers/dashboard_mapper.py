"""Aggregate query rows to the dashboard responses. Rates are fractions (0.125 = 12.5%); the
web app formats them.
"""

from returnright.domain.enums import ReturnReason
from returnright.dtos.responses.dashboard import (
    CategoryReturnRateResponse,
    FlaggedCustomerResponse,
    ReasonCountResponse,
)
from returnright.repositories.dashboard_repository import CategoryCounts, FlaggedCustomerRow


def to_category_rate(counts: CategoryCounts) -> CategoryReturnRateResponse:
    rate = counts.returns / counts.orders if counts.orders else 0.0
    return CategoryReturnRateResponse(
        category=counts.category,
        orders=counts.orders,
        returns=counts.returns,
        return_rate=round(rate, 4),
    )


def to_reason_count(code: str, count: int) -> ReasonCountResponse:
    return ReasonCountResponse(reason=ReturnReason[code], count=count)


def to_flagged_customer(row: FlaggedCustomerRow) -> FlaggedCustomerResponse:
    return FlaggedCustomerResponse(
        customer_id=row.customer_id, name=row.name, returns_last_30_days=row.returns_in_window
    )
