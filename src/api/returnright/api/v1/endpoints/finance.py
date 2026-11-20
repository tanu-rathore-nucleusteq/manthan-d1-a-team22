"""Finance reviewer: list returns awaiting approval, approve or reject them, pay approved refunds
and retry failed ones. Store credit is recorded in the ledger without calling the gateway.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from returnright.api.deps import (
    ApprovalServiceDep,
    FinanceReviewer,
    IdempotencyKey,
    Pagination,
    RefundServiceDep,
    ReturnCode,
)
from returnright.domain.enums import RefundStatus
from returnright.dtos.internal.audit import Actor
from returnright.dtos.requests.finance import ApprovalDecisionRequest
from returnright.dtos.responses.common import ErrorResponse, PageResponse
from returnright.dtos.responses.finance import (
    LedgerEntryResponse,
    PendingApprovalResponse,
    RefundResponse,
)

router = APIRouter(prefix="/finance", tags=["finance"])

RefundId = Annotated[int, Path(gt=0)]


@router.get(
    "/approvals",
    response_model=PageResponse[PendingApprovalResponse],
    summary="Returns whose refund total is above the approval threshold",
)
def list_pending_approvals(
    user: FinanceReviewer, service: ApprovalServiceDep, page: Pagination
) -> PageResponse[PendingApprovalResponse]:
    return service.queue(page.page, page.size)


@router.post(
    "/approvals/{return_code}/decision",
    response_model=PendingApprovalResponse,
    summary="Approve or reject a refund above the threshold",
    responses={
        404: {"model": ErrorResponse, "description": "No return has this code"},
        409: {"model": ErrorResponse, "description": "Already decided, or not waiting"},
    },
)
def decide_approval(
    return_code: ReturnCode,
    payload: ApprovalDecisionRequest,
    user: FinanceReviewer,
    service: ApprovalServiceDep,
) -> PendingApprovalResponse:
    return service.decide(return_code, user, payload.approve, payload.comment)


@router.get("/refunds", response_model=PageResponse[RefundResponse], summary="Refunds by status")
def list_refunds(
    user: FinanceReviewer,
    service: RefundServiceDep,
    page: Pagination,
    status: Annotated[RefundStatus | None, Query()] = None,
) -> PageResponse[RefundResponse]:
    return service.page(status, page.page, page.size)


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    summary="One refund",
    responses={404: {"model": ErrorResponse, "description": "No refund has this id"}},
)
def get_refund(
    refund_id: RefundId, user: FinanceReviewer, service: RefundServiceDep
) -> RefundResponse:
    return service.detail(refund_id)


@router.post(
    "/refunds/{refund_id}/pay",
    response_model=RefundResponse,
    summary="Pay an approved refund, or retry a failed one, through the gateway (idempotent)",
    description=(
        "Use this to retry a refund whose gateway call failed or timed out. Send the same "
        "Idempotency-Key on every retry: the gateway call always uses refund-<return_item_id>, "
        "so a refund is never paid twice."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "No refund has this id"},
        409: {"model": ErrorResponse, "description": "Waiting for approval, or rejected"},
    },
)
def pay_refund(
    refund_id: RefundId,
    idempotency_key: IdempotencyKey,
    user: FinanceReviewer,
    service: RefundServiceDep,
) -> RefundResponse:
    return service.pay_and_describe(refund_id, Actor.staff(user), idempotency_key)


@router.get(
    "/ledger",
    response_model=PageResponse[LedgerEntryResponse],
    summary="Ledger of gateway refunds and store credit",
)
def list_ledger(
    user: FinanceReviewer,
    service: RefundServiceDep,
    page: Pagination,
    refund_id: Annotated[int | None, Query(gt=0)] = None,
) -> PageResponse[LedgerEntryResponse]:
    return service.ledger(refund_id, page.page, page.size)
