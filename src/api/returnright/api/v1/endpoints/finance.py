"""Finance reviewer: list returns awaiting approval, approve or reject them, pay approved refunds
and retry failed ones. Store credit is recorded in the ledger without calling the gateway.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from returnright.api.deps import (
    DbSession,
    FinanceReviewer,
    IdempotencyKey,
    Pagination,
    ReturnCode,
)
from returnright.api.not_implemented import not_implemented
from returnright.domain.enums import RefundStatus
from returnright.dtos.requests.finance import ApprovalDecisionRequest
from returnright.dtos.responses.common import PageResponse
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
    user: FinanceReviewer, db: DbSession, page: Pagination
) -> PageResponse[PendingApprovalResponse]:
    not_implemented("Pending approvals")


@router.post(
    "/approvals/{return_code}/decision",
    response_model=PendingApprovalResponse,
    summary="Approve or reject a refund above the threshold",
    responses={409: {"description": "Already decided"}},
)
def decide_approval(
    return_code: ReturnCode,
    payload: ApprovalDecisionRequest,
    user: FinanceReviewer,
    db: DbSession,
) -> PendingApprovalResponse:
    not_implemented("Approval decision")


@router.get("/refunds", response_model=PageResponse[RefundResponse], summary="Refunds by status")
def list_refunds(
    user: FinanceReviewer,
    db: DbSession,
    page: Pagination,
    status: Annotated[RefundStatus | None, Query()] = None,
) -> PageResponse[RefundResponse]:
    not_implemented("Refund list")


@router.get("/refunds/{refund_id}", response_model=RefundResponse, summary="One refund")
def get_refund(refund_id: RefundId, user: FinanceReviewer, db: DbSession) -> RefundResponse:
    not_implemented("Refund details")


@router.post(
    "/refunds/{refund_id}/pay",
    response_model=RefundResponse,
    summary="Pay an approved refund, or retry a failed one, through the gateway (idempotent)",
    description=(
        "Use this to retry a refund whose gateway call failed or timed out. Send the same "
        "Idempotency-Key on every retry: the gateway call always uses refund-<return_item_id>, "
        "so a refund is never paid twice."
    ),
    responses={409: {"description": "Not approved, or already paid with another key"}},
)
def pay_refund(
    refund_id: RefundId,
    idempotency_key: IdempotencyKey,
    user: FinanceReviewer,
    db: DbSession,
) -> RefundResponse:
    not_implemented("Refund payment")


@router.get(
    "/ledger",
    response_model=PageResponse[LedgerEntryResponse],
    summary="Ledger of gateway refunds and store credit",
)
def list_ledger(
    user: FinanceReviewer,
    db: DbSession,
    page: Pagination,
    refund_id: Annotated[int | None, Query(gt=0)] = None,
) -> PageResponse[LedgerEntryResponse]:
    not_implemented("Ledger")
