"""Every 4xx and 5xx leaves the API as one ErrorResponse shape: `code`, `message`,
`request_id`, plus `errors` per field for invalid input. Messages are safe to show and never
carry internal details.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from returnright.core.constants import REQUEST_ID_HEADER
from returnright.core.exceptions import (
    AlreadyDecidedError,
    CannotDeactivateSelfError,
    ConcurrentUpdateError,
    DomainError,
    DuplicateReturnError,
    InspectionMismatchError,
    InvalidCredentialsError,
    InvalidDateRangeError,
    InvalidReturnRequestError,
    InvalidTransitionError,
    ItemNotEligibleError,
    LabelUnavailableError,
    NoPendingApprovalError,
    OrderNotFoundError,
    PhotoRejectedError,
    PhotoTooLargeError,
    RefundNotFoundError,
    RefundNotPayableError,
    ReturnNotFoundError,
    StaffLoginTakenError,
    StaffNotFoundError,
)
from returnright.core.logging import request_id_var
from returnright.dtos.responses.common import ErrorResponse, FieldError

logger = logging.getLogger(__name__)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    OrderNotFoundError: status.HTTP_404_NOT_FOUND,
    ReturnNotFoundError: status.HTTP_404_NOT_FOUND,
    RefundNotFoundError: status.HTTP_404_NOT_FOUND,
    StaffNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidDateRangeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidReturnRequestError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ItemNotEligibleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InspectionMismatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PhotoRejectedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PhotoTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    DuplicateReturnError: status.HTTP_409_CONFLICT,
    InvalidTransitionError: status.HTTP_409_CONFLICT,
    ConcurrentUpdateError: status.HTTP_409_CONFLICT,
    NoPendingApprovalError: status.HTTP_409_CONFLICT,
    AlreadyDecidedError: status.HTTP_409_CONFLICT,
    LabelUnavailableError: status.HTTP_409_CONFLICT,
    RefundNotPayableError: status.HTTP_409_CONFLICT,
    StaffLoginTakenError: status.HTTP_409_CONFLICT,
    CannotDeactivateSelfError: status.HTTP_409_CONFLICT,
}

CODE_BY_HTTP_STATUS = {
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
}


def _status_for(error: DomainError) -> int:
    for error_type in type(error).__mro__:
        if error_type in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[error_type]
    return status.HTTP_400_BAD_REQUEST


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request_id_var.get()


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    body = ErrorResponse(code=code, message=message, request_id=request_id, errors=errors)
    headers = dict(headers or {})
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code, content=body.model_dump(exclude_none=True), headers=headers
    )


async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    return _error_response(request, _status_for(error), error.code, error.message)


async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    errors = [
        FieldError(
            field=".".join(str(part) for part in item["loc"] if part != "body"),
            message=item["msg"],
        )
        for item in error.errors()
    ]
    return _error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation_error",
        "Some details are missing or not valid. Check the highlighted fields.",
        errors,
    )


async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
    message = error.detail if isinstance(error.detail, str) else "The request was not accepted."
    return _error_response(
        request,
        error.status_code,
        CODE_BY_HTTP_STATUS.get(error.status_code, "http_error"),
        message,
        headers=error.headers,
    )


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception("unhandled error", extra={"request_id": _request_id(request)})
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "Something went wrong on our side. Please try again in a moment.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
