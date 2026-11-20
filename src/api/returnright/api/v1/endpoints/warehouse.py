"""Warehouse agent: find a return by QR code, mark it received, record grades A, B or C, and
accept, partially accept or reject.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from returnright.api.deps import DbSession, Pagination, ReturnCode, WarehouseAgent
from returnright.api.not_implemented import not_implemented
from returnright.domain.enums import ReturnStatus
from returnright.dtos.requests.warehouse import InspectionRequest
from returnright.dtos.responses.common import PageResponse
from returnright.dtos.responses.returns import ReturnDetailResponse, ReturnSummaryResponse
from returnright.dtos.responses.warehouse import InspectionResultResponse

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


@router.get(
    "/returns",
    response_model=PageResponse[ReturnSummaryResponse],
    summary="Work queue of returns, filtered by status",
)
def list_returns(
    user: WarehouseAgent,
    db: DbSession,
    page: Pagination,
    status: Annotated[ReturnStatus | None, Query()] = ReturnStatus.IN_TRANSIT,
) -> PageResponse[ReturnSummaryResponse]:
    not_implemented("Warehouse queue")


@router.get(
    "/returns/{return_code}",
    response_model=ReturnDetailResponse,
    summary="Find a return by its QR code",
)
def get_return(
    return_code: ReturnCode, user: WarehouseAgent, db: DbSession
) -> ReturnDetailResponse:
    not_implemented("Warehouse return lookup")


@router.post(
    "/returns/{return_code}/receive",
    response_model=ReturnDetailResponse,
    summary="Mark the parcel received (In transit → Received)",
    responses={409: {"description": "The return is not In transit"}},
)
def receive_return(
    return_code: ReturnCode, user: WarehouseAgent, db: DbSession
) -> ReturnDetailResponse:
    not_implemented("Receive return")


@router.post(
    "/returns/{return_code}/inspection",
    response_model=InspectionResultResponse,
    summary="Grade each item A, B or C and accept or reject it (Received → Inspected)",
    responses={409: {"description": "The return is not Received"}},
)
def inspect_return(
    return_code: ReturnCode, payload: InspectionRequest, user: WarehouseAgent, db: DbSession
) -> InspectionResultResponse:
    not_implemented("Inspection")
