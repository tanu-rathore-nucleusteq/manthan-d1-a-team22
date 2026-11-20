"""Operations manager: read the audit log of every state change."""

from typing import Annotated

from fastapi import APIRouter, Query

from returnright.api.deps import AuditLogServiceDep, OperationsManager, Pagination, ReturnCode
from returnright.dtos.responses.audit import AuditLogResponse
from returnright.dtos.responses.common import PageResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PageResponse[AuditLogResponse], summary="Audit log, newest first")
def list_audit_entries(
    user: OperationsManager,
    audit: AuditLogServiceDep,
    page: Pagination,
    entity: Annotated[
        str | None, Query(max_length=50, description="return, refund or customer")
    ] = None,
    entity_id: Annotated[int | None, Query(gt=0)] = None,
) -> PageResponse[AuditLogResponse]:
    return audit.page(entity, entity_id, page.page, page.size)


@router.get(
    "/returns/{return_code}",
    response_model=list[AuditLogResponse],
    summary="Everything recorded for one return, oldest first",
)
def get_return_audit(
    return_code: ReturnCode, user: OperationsManager, audit: AuditLogServiceDep
) -> list[AuditLogResponse]:
    return audit.for_return(return_code)
