"""Base classes, shared types and validation patterns for every DTO."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2, ge=0)]
"""An amount in INR with two decimal places. Never use float for money."""

SignedMoney = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]
"""Money that can be negative, such as a ledger reversal."""

ORDER_NUMBER_PATTERN = r"^[A-Za-z0-9-]{4,32}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RequestDTO(BaseModel):
    """Inbound API payload: unknown fields are rejected and strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseDTO(BaseModel):
    """Outbound API payload: can be built straight from ORM objects or dataclasses."""

    model_config = ConfigDict(from_attributes=True)
