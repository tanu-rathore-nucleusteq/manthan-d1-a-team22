"""The finance reviewer's decision on a refund above the approval threshold."""

from pydantic import Field

from returnright.dtos.base import RequestDTO


class ApprovalDecisionRequest(RequestDTO):
    approve: bool
    comment: str | None = Field(default=None, max_length=500)
