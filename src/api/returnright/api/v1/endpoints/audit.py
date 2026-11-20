"""Operations manager: read the audit log of every state change."""

from typing import Annotated

from fastapi import APIRouter, Query

from returnright.api.deps import DbSession, OperationsManager, Pagination, ReturnCode
from returnright.api.not_implemented import not_implemented
from returnright.dtos.responses.audit import AuditLogResponse
from returnright.dtos.responses.common import PageResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PageResponse[AuditLogResponse], summary="Audit log, newest first")
def list_audit_entries(
    user: OperationsManager,
    db: DbSession,
    page: Pagination,
    entity: Annotated[str | None, Query(max_length=50)] = None,
    entity_id: Annotated[int | None, Query(gt=0)] = None,
) -> PageResponse[AuditLogResponse]:
    not_implemented("Audit log")


@router.get(
    "/returns/{return_code}",
    response_model=list[AuditLogResponse],
    summary="Every state change of one return, oldest first",
)
def get_return_audit(
    return_code: ReturnCode, user: OperationsManager, db: DbSession
) -> list[AuditLogResponse]:
    not_implemented("Return audit trail")
