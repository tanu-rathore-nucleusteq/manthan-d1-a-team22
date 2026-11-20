"""Result of a warehouse inspection."""

from returnright.domain.enums import ReturnStatus
from returnright.dtos.base import Money, ResponseDTO
from returnright.dtos.responses.returns import ReturnItemResponse


class InspectionResultResponse(ResponseDTO):
    return_code: str
    status: ReturnStatus
    items: list[ReturnItemResponse]
    refund_total: Money
    needs_finance_approval: bool
