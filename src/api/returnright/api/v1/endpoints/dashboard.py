"""Operations manager: return rate by category, top reasons, average cycle time, flagged
customers.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from returnright.api.deps import DbSession, OperationsManager
from returnright.api.not_implemented import not_implemented
from returnright.dtos.responses.dashboard import (
    CategoryReturnRateResponse,
    DashboardResponse,
    FlaggedCustomerResponse,
    ReasonCountResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DateFrom = Annotated[date | None, Query(description="Inclusive start date")]
DateTo = Annotated[date | None, Query(description="Inclusive end date")]


@router.get("", response_model=DashboardResponse, summary="All dashboard metrics in one call")
def get_dashboard(
    user: OperationsManager, db: DbSession, date_from: DateFrom = None, date_to: DateTo = None
) -> DashboardResponse:
    not_implemented("Dashboard")


@router.get(
    "/return-rates",
    response_model=list[CategoryReturnRateResponse],
    summary="Return rate by category",
)
def get_return_rates(
    user: OperationsManager, db: DbSession, date_from: DateFrom = None, date_to: DateTo = None
) -> list[CategoryReturnRateResponse]:
    not_implemented("Return rate by category")


@router.get("/top-reasons", response_model=list[ReasonCountResponse], summary="Top return reasons")
def get_top_reasons(
    user: OperationsManager,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[ReasonCountResponse]:
    not_implemented("Top reasons")


@router.get(
    "/flagged-customers",
    response_model=list[FlaggedCustomerResponse],
    summary="Customers with more than 3 returns in 30 days",
)
def get_flagged_customers(user: OperationsManager, db: DbSession) -> list[FlaggedCustomerResponse]:
    not_implemented("Flagged customers")
