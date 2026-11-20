"""Response shapes shared by every endpoint."""

from returnright.dtos.base import ResponseDTO


class ErrorResponse(ResponseDTO):
    code: str
    message: str
    request_id: str | None = None


class PageResponse[ItemT](ResponseDTO):
    items: list[ItemT]
    total: int
    page: int
    size: int
