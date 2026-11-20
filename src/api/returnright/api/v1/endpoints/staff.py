"""Operations manager: the team's staff accounts. There is no self sign-up; the manager adds
each account with a temporary password and can switch it off.
"""

from typing import Annotated

from fastapi import APIRouter, Path, status

from returnright.api.deps import OperationsManager, StaffServiceDep
from returnright.dtos.requests.staff import CreateStaffRequest, UpdateStaffRequest
from returnright.dtos.responses.common import ErrorResponse
from returnright.dtos.responses.staff import StaffMemberResponse

router = APIRouter(prefix="/staff", tags=["staff"])

StaffId = Annotated[int, Path(gt=0)]


@router.get("", response_model=list[StaffMemberResponse], summary="Every staff account")
def list_staff(user: OperationsManager, staff: StaffServiceDep) -> list[StaffMemberResponse]:
    return staff.team()


@router.post(
    "",
    response_model=StaffMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a staff account with a temporary password",
    responses={409: {"model": ErrorResponse, "description": "The email or username is taken"}},
)
def create_staff(
    payload: CreateStaffRequest, user: OperationsManager, staff: StaffServiceDep
) -> StaffMemberResponse:
    return staff.create(payload, user)


@router.patch(
    "/{staff_id}",
    response_model=StaffMemberResponse,
    summary="Switch a staff account off or on",
    responses={
        404: {"model": ErrorResponse, "description": "No staff account has this id"},
        409: {"model": ErrorResponse, "description": "Managers can't switch themselves off"},
    },
)
def update_staff(
    staff_id: StaffId, payload: UpdateStaffRequest, user: OperationsManager, staff: StaffServiceDep
) -> StaffMemberResponse:
    return staff.update(staff_id, payload, user)
