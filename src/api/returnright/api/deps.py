"""FastAPI dependencies: database session, CurrentUser from the JWT, and require_role(...) for
each internal role.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from returnright.api.not_implemented import not_implemented
from returnright.core.config import Settings, get_settings
from returnright.core.constants import (
    CUSTOMER_EMAIL_HEADER,
    DEFAULT_PAGE_SIZE,
    IDEMPOTENCY_KEY_HEADER,
    MAX_PAGE_SIZE,
)
from returnright.db.session import get_db
from returnright.domain.enums import Role
from returnright.dtos.base import EMAIL_PATTERN
from returnright.dtos.internal.auth import CurrentUser

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

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
) -> CurrentUser:
    """Resolve the caller from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    not_implemented("JWT verification")


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
OperationsManager = Annotated[CurrentUser, Depends(require_role(Role.OPS_MANAGER))]
