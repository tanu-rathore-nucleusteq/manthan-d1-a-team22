"""Customer returns: create a return, upload its photo (multipart), get the label and QR code,
view the status timeline, mark it shipped.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from returnright.api.deps import AppSettings, CustomerEmail, DbSession, ReturnCode
from returnright.api.not_implemented import not_implemented
from returnright.dtos.base import EMAIL_PATTERN
from returnright.dtos.requests.returns import CreateReturnRequest, CustomerProofRequest
from returnright.dtos.responses.returns import (
    PhotoUploadResponse,
    ReturnDetailResponse,
    ReturnLabelResponse,
    StatusEventResponse,
)

router = APIRouter(prefix="/returns", tags=["customer: returns"])


@router.post(
    "",
    response_model=ReturnDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a return for one or more items",
    responses={422: {"description": "An item is not eligible; the reason is in the message"}},
)
def create_return(payload: CreateReturnRequest, db: DbSession) -> ReturnDetailResponse:
    not_implemented("Create return")


@router.post(
    "/{return_code}/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo of the item (JPEG or PNG, stored locally)",
    responses={413: {"description": "File larger than UPLOAD_MAX_MB"}},
)
def upload_photo(
    return_code: ReturnCode,
    email: Annotated[str, Form(max_length=254, pattern=EMAIL_PATTERN)],
    photo: Annotated[UploadFile, File(description="JPEG or PNG")],
    db: DbSession,
    settings: AppSettings,
) -> PhotoUploadResponse:
    not_implemented("Photo upload")


@router.get("/{return_code}", response_model=ReturnDetailResponse, summary="Return details")
def get_return(
    return_code: ReturnCode, email: CustomerEmail, db: DbSession
) -> ReturnDetailResponse:
    not_implemented("Return details")


@router.get(
    "/{return_code}/timeline",
    response_model=list[StatusEventResponse],
    summary="Status timeline: Requested → … → Refunded or Rejected",
)
def get_timeline(
    return_code: ReturnCode, email: CustomerEmail, db: DbSession
) -> list[StatusEventResponse]:
    not_implemented("Status timeline")


@router.get(
    "/{return_code}/label",
    response_model=ReturnLabelResponse,
    summary="Mock return label with a QR code",
)
def get_label(return_code: ReturnCode, email: CustomerEmail, db: DbSession) -> ReturnLabelResponse:
    not_implemented("Return label")


@router.post(
    "/{return_code}/ship",
    response_model=ReturnDetailResponse,
    summary="Customer confirms the parcel is shipped (Approved → In transit)",
    responses={409: {"description": "The return is not in the Approved state"}},
)
def mark_shipped(
    return_code: ReturnCode, payload: CustomerProofRequest, db: DbSession
) -> ReturnDetailResponse:
    not_implemented("Mark shipped")
