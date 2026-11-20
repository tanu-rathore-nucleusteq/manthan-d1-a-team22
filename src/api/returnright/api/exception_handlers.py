"""Maps domain errors to HTTP responses (409 invalid transition, 422 not eligible) as
ErrorResponse, with safe messages and no internal details.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from returnright.core.constants import REQUEST_ID_HEADER
from returnright.core.exceptions import DomainError, OrderNotFoundError
from returnright.dtos.responses.common import ErrorResponse

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    OrderNotFoundError: status.HTTP_404_NOT_FOUND,
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
