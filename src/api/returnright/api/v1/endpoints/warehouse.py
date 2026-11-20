"""Warehouse agent: find a return by QR code, mark it received, record grades A, B or C, and
accept, partially accept or reject.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from returnright.api.deps import (
    InspectionServiceDep,
    Pagination,
    ReturnCode,
    ReturnReviewer,
    WarehouseAgent,
)
from returnright.domain.enums import ReturnStatus
from returnright.dtos.requests.warehouse import InspectionRequest
from returnright.dtos.responses.common import ErrorResponse, PageResponse
from returnright.dtos.responses.returns import ReturnDetailResponse, ReturnSummaryResponse
from returnright.dtos.responses.warehouse import InspectionResultResponse

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "No return has this code"}}


@router.get(
    "/returns",
    response_model=PageResponse[ReturnSummaryResponse],
    summary="Work queue of returns, filtered by status",
)
def list_returns(
    user: WarehouseAgent,
    service: InspectionServiceDep,
    page: Pagination,
    status: Annotated[ReturnStatus | None, Query()] = ReturnStatus.IN_TRANSIT,
) -> PageResponse[ReturnSummaryResponse]:
    return service.queue(status, page.page, page.size)


@router.get(
    "/returns/{return_code}",
    response_model=ReturnDetailResponse,
    summary="Find a return by its QR code",
    responses=NOT_FOUND,
)
def get_return(
    return_code: ReturnCode, user: ReturnReviewer, service: InspectionServiceDep
) -> ReturnDetailResponse:
    return service.detail(return_code)


@router.post(
    "/returns/{return_code}/receive",
    response_model=ReturnDetailResponse,
    summary="Mark the parcel received (In transit → Received)",
    responses={
        **NOT_FOUND,
        409: {
            "model": ErrorResponse,
            "description": "Already received (code already_received), or not shipped yet",
        },
    },
)
def receive_return(
    return_code: ReturnCode, user: WarehouseAgent, service: InspectionServiceDep
) -> ReturnDetailResponse:
    return service.receive(return_code, user)


@router.post(
    "/returns/{return_code}/inspection",
    response_model=InspectionResultResponse,
    summary="Grade each item A, B or C and accept or reject it (Received → Inspected)",
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "Not received yet, or already inspected"},
        422: {"model": ErrorResponse, "description": "Not every item graded exactly once"},
    },
)
def inspect_return(
    return_code: ReturnCode,
    payload: InspectionRequest,
    user: WarehouseAgent,
    service: InspectionServiceDep,
) -> InspectionResultResponse:
    return service.inspect(return_code, user, payload)
