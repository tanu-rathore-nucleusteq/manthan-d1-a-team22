"""FastAPI dependencies: database session, CurrentUser from the JWT, and require_role(...) for
each internal role.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from returnright.core.config import Settings, get_settings
from returnright.core.constants import (
    CUSTOMER_EMAIL_HEADER,
    DEFAULT_PAGE_SIZE,
    IDEMPOTENCY_KEY_HEADER,
    MAX_PAGE_SIZE,
)
from returnright.core.security import decode_access_token
from returnright.db.session import get_db
from returnright.domain.enums import Role
from returnright.dtos.base import EMAIL_PATTERN
from returnright.dtos.internal.auth import CurrentUser
from returnright.integrations.payment_gateway import HttpPaymentGateway, http_client
from returnright.interfaces.payment_gateway import PaymentGateway
from returnright.repositories.order_repository import OrderRepository
from returnright.repositories.user_repository import StaffUserRepository
from returnright.services.approval_service import ApprovalService
from returnright.services.audit_service import AuditLogService
from returnright.services.auth_service import AuthService
from returnright.services.dashboard_service import DashboardService
from returnright.services.inspection_service import InspectionService
from returnright.services.order_service import OrderService
from returnright.services.refund_service import RefundService
from returnright.services.return_service import ReturnService
from returnright.services.staff_service import StaffService
from returnright.utils.clock import Clock, get_clock

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
AppClock = Annotated[Clock, Depends(get_clock)]


# --- Services --------------------------------------------------------------------------------


def get_order_service(db: DbSession, clock: AppClock) -> OrderService:
    return OrderService(OrderRepository(db), clock)


def get_auth_service(db: DbSession, settings: AppSettings, clock: AppClock) -> AuthService:
    return AuthService(StaffUserRepository(db), settings, clock)


def get_payment_gateway(settings: AppSettings) -> PaymentGateway:
    client = http_client(settings.gateway_url, settings.gateway_timeout_seconds)
    return HttpPaymentGateway(client, settings.gateway_max_retries)


PaymentGatewayDep = Annotated[PaymentGateway, Depends(get_payment_gateway)]


def get_return_service(db: DbSession, settings: AppSettings, clock: AppClock) -> ReturnService:
    return ReturnService(db, settings, clock)


def get_refund_service(db: DbSession, clock: AppClock, gateway: PaymentGatewayDep) -> RefundService:
    return RefundService(db, gateway, clock)


RefundServiceDep = Annotated[RefundService, Depends(get_refund_service)]


def get_inspection_service(
    db: DbSession, settings: AppSettings, clock: AppClock, refunds: RefundServiceDep
) -> InspectionService:
    return InspectionService(db, settings, clock, refunds)


def get_approval_service(
    db: DbSession, clock: AppClock, refunds: RefundServiceDep
) -> ApprovalService:
    return ApprovalService(db, clock, refunds)


def get_dashboard_service(db: DbSession, clock: AppClock) -> DashboardService:
    return DashboardService(db, clock)


def get_audit_log_service(db: DbSession) -> AuditLogService:
    return AuditLogService(db)


def get_staff_service(db: DbSession) -> StaffService:
    return StaffService(db)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ReturnServiceDep = Annotated[ReturnService, Depends(get_return_service)]
InspectionServiceDep = Annotated[InspectionService, Depends(get_inspection_service)]
ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
AuditLogServiceDep = Annotated[AuditLogService, Depends(get_audit_log_service)]
StaffServiceDep = Annotated[StaffService, Depends(get_staff_service)]

# --- Path and header parameters shared by several routers ---------------------------------

ReturnCode = Annotated[
    str,
    Path(
        min_length=6,
        max_length=32,
        pattern=r"^[A-Za-z0-9-]+$",
        description="Return code on the QR label",
    ),
]
CustomerEmail = Annotated[
    str,
    Header(alias=CUSTOMER_EMAIL_HEADER, max_length=254, pattern=EMAIL_PATTERN),
]
IdempotencyKey = Annotated[
    str,
    Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=64),
]


# --- Pagination ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, size=size)


Pagination = Annotated[PageParams, Depends(page_params)]


# --- Authentication and roles ----------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False, description="JWT from POST /api/v1/auth/login")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: AppSettings,
) -> CurrentUser:
    """Resolve the caller from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(credentials.credentials, settings)
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired or is not valid. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def require_role(*roles: Role) -> Callable[..., CurrentUser]:
    """Dependency factory: the caller must hold one of the given roles."""

    def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return user

    return checker


AnyStaff = Annotated[CurrentUser, Depends(require_role(*Role))]
WarehouseAgent = Annotated[CurrentUser, Depends(require_role(Role.WAREHOUSE_AGENT))]
FinanceReviewer = Annotated[CurrentUser, Depends(require_role(Role.FINANCE_REVIEWER))]
# Read-only return detail: finance needs item names, grades and photos to decide an approval.
WarehouseOrFinance = Annotated[
    CurrentUser, Depends(require_role(Role.WAREHOUSE_AGENT, Role.FINANCE_REVIEWER))
]
OperationsManager = Annotated[CurrentUser, Depends(require_role(Role.OPS_MANAGER))]
