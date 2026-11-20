"""Placeholder for planned endpoints: input is validated, then 501 names the missing feature.
Delete each call as its story lands; see docs/api-plan.md.
"""

from typing import NoReturn

from fastapi import HTTPException, status


def not_implemented(feature: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature} is planned but not implemented yet",
    )
