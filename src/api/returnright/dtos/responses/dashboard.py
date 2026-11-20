"""Manager dashboard metrics."""

from datetime import datetime

from returnright.domain.enums import ReturnReason
from returnright.dtos.base import ResponseDTO


class CategoryReturnRateResponse(ResponseDTO):
    category: str
    orders: int
    returns: int
    return_rate: float


class ReasonCountResponse(ResponseDTO):
    reason: ReturnReason
    count: int


class FlaggedCustomerResponse(ResponseDTO):
    customer_id: int
    name: str
    returns_last_30_days: int


class DashboardResponse(ResponseDTO):
    return_rate_by_category: list[CategoryReturnRateResponse]
    top_reasons: list[ReasonCountResponse]
    average_cycle_time_hours: float | None
    flagged_customers: list[FlaggedCustomerResponse]
    generated_at: datetime
