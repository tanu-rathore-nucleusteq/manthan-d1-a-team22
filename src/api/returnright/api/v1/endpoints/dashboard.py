"""Operations manager: return rate by category, top reasons, average cycle time, flagged
customers. The web app draws the charts from these numbers.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from returnright.api.deps import DashboardServiceDep, OperationsManager
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
    user: OperationsManager,
    dashboard: DashboardServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
) -> DashboardResponse:
    return dashboard.dashboard(date_from, date_to)


@router.get(
    "/return-rates",
    response_model=list[CategoryReturnRateResponse],
    summary="Return rate by category",
)
def get_return_rates(
    user: OperationsManager,
    dashboard: DashboardServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
) -> list[CategoryReturnRateResponse]:
    return dashboard.return_rates(date_from, date_to)


@router.get("/top-reasons", response_model=list[ReasonCountResponse], summary="Top return reasons")
def get_top_reasons(
    user: OperationsManager,
    dashboard: DashboardServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[ReasonCountResponse]:
    return dashboard.top_reasons(date_from, date_to, limit)


@router.get(
    "/flagged-customers",
    response_model=list[FlaggedCustomerResponse],
    summary="Customers with more than 3 returns in 30 days",
)
def get_flagged_customers(
    user: OperationsManager, dashboard: DashboardServiceDep
) -> list[FlaggedCustomerResponse]:
    return dashboard.flagged_customers()
