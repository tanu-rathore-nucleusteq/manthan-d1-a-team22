"""Response shapes shared by every endpoint."""

from returnright.dtos.base import ResponseDTO


class FieldError(ResponseDTO):
    field: str
    message: str


class ErrorResponse(ResponseDTO):
    code: str
    message: str
    request_id: str | None = None
    errors: list[FieldError] | None = None


class PageResponse[ItemT](ResponseDTO):
    items: list[ItemT]
    total: int
    page: int
    size: int
