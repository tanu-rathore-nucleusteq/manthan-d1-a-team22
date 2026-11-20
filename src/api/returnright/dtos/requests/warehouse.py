"""Warehouse inspection payload: a grade and a decision for every returned item."""

from pydantic import Field

from returnright.domain.enums import Grade, ItemDecision
from returnright.dtos.base import RequestDTO


class ItemInspectionRequest(RequestDTO):
    return_item_id: int = Field(gt=0)
    grade: Grade
    decision: ItemDecision
    notes: str | None = Field(default=None, max_length=500)


class InspectionRequest(RequestDTO):
    items: list[ItemInspectionRequest] = Field(min_length=1, max_length=20)
