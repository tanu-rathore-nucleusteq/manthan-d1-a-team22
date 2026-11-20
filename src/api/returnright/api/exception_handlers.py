"""Maps domain errors to HTTP responses (409 invalid transition, 422 not eligible) as
ErrorResponse, with safe messages and no internal details.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from returnright.core.constants import REQUEST_ID_HEADER
from returnright.core.exceptions import (
    ConcurrentUpdateError,
    DomainError,
    DuplicateReturnError,
    InspectionMismatchError,
    InvalidCredentialsError,
    InvalidReturnRequestError,
    InvalidTransitionError,
    ItemNotEligibleError,
    NoPendingApprovalError,
    OrderNotFoundError,
    PhotoRejectedError,
    PhotoTooLargeError,
    RefundNotFoundError,
    RefundNotPayableError,
    ReturnNotFoundError,
)
from returnright.dtos.responses.common import ErrorResponse

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    OrderNotFoundError: status.HTTP_404_NOT_FOUND,
    ReturnNotFoundError: status.HTTP_404_NOT_FOUND,
    RefundNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidReturnRequestError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ItemNotEligibleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InspectionMismatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PhotoRejectedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PhotoTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    DuplicateReturnError: status.HTTP_409_CONFLICT,
    InvalidTransitionError: status.HTTP_409_CONFLICT,
    ConcurrentUpdateError: status.HTTP_409_CONFLICT,
    NoPendingApprovalError: status.HTTP_409_CONFLICT,
    RefundNotPayableError: status.HTTP_409_CONFLICT,
}


def _status_for(error: DomainError) -> int:
    for error_type in type(error).__mro__:
        if error_type in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[error_type]
    return status.HTTP_400_BAD_REQUEST


async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    body = ErrorResponse(
        code=error.code,
        message=error.message,
        request_id=request.headers.get(REQUEST_ID_HEADER),
    )
    return JSONResponse(status_code=_status_for(error), content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
