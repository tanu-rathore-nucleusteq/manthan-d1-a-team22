"""Customer returns: create a return, upload a photo per item (multipart), get the label and QR
code, view the status timeline, mark it shipped.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from returnright.api.deps import CustomerEmail, ReturnCode, ReturnServiceDep
from returnright.dtos.base import EMAIL_PATTERN
from returnright.dtos.requests.returns import CreateReturnRequest, CustomerProofRequest
from returnright.dtos.responses.common import ErrorResponse
from returnright.dtos.responses.returns import (
    PhotoUploadResponse,
    ReturnDetailResponse,
    ReturnLabelResponse,
    StatusEventResponse,
)

router = APIRouter(prefix="/returns", tags=["customer: returns"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "No return matches this code and email"}}


@router.post(
    "",
    response_model=ReturnDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a return for one or more items",
    responses={
        404: {"model": ErrorResponse, "description": "No order matches this number and email"},
        409: {
            "model": ErrorResponse,
            "description": "An item is already in an open return (for example a double submit)",
        },
        422: {
            "model": ErrorResponse,
            "description": "An item is not eligible; the reason is in the message",
        },
    },
)
def create_return(payload: CreateReturnRequest, service: ReturnServiceDep) -> ReturnDetailResponse:
    return service.create(payload)


@router.post(
    "/{return_code}/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo of one returned item (JPEG or PNG, stored locally)",
    responses={
        **NOT_FOUND,
        413: {"model": ErrorResponse, "description": "File larger than UPLOAD_MAX_MB"},
        422: {"model": ErrorResponse, "description": "Not a JPEG or PNG, or too many photos"},
    },
)
def upload_photo(
    return_code: ReturnCode,
    email: Annotated[str, Form(max_length=254, pattern=EMAIL_PATTERN)],
    return_item_id: Annotated[int, Form(gt=0)],
    photo: Annotated[UploadFile, File(description="JPEG or PNG")],
    service: ReturnServiceDep,
) -> PhotoUploadResponse:
    return service.upload_photo(return_code, email, return_item_id, photo.file)


@router.get(
    "/{return_code}",
    response_model=ReturnDetailResponse,
    summary="Return details",
    responses=NOT_FOUND,
)
def get_return(
    return_code: ReturnCode, email: CustomerEmail, service: ReturnServiceDep
) -> ReturnDetailResponse:
    return service.detail(return_code, email)


@router.get(
    "/{return_code}/timeline",
    response_model=list[StatusEventResponse],
    summary="Status timeline: Requested → … → Refunded or Rejected",
    responses=NOT_FOUND,
)
def get_timeline(
    return_code: ReturnCode, email: CustomerEmail, service: ReturnServiceDep
) -> list[StatusEventResponse]:
    return service.timeline(return_code, email)


@router.get(
    "/{return_code}/label",
    response_model=ReturnLabelResponse,
    summary="Mock return label with a QR code",
    responses={**NOT_FOUND, 409: {"model": ErrorResponse, "description": "Return rejected"}},
)
def get_label(
    return_code: ReturnCode, email: CustomerEmail, service: ReturnServiceDep
) -> ReturnLabelResponse:
    return service.label(return_code, email)


@router.post(
    "/{return_code}/ship",
    response_model=ReturnDetailResponse,
    summary="Customer confirms the parcel is shipped (Approved → In transit)",
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "The return is not in the Approved state"},
    },
)
def mark_shipped(
    return_code: ReturnCode, payload: CustomerProofRequest, service: ReturnServiceDep
) -> ReturnDetailResponse:
    return service.ship(return_code, payload.email)
