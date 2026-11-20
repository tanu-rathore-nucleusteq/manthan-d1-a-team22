"""POST /auth/login for internal roles: warehouse agent, finance reviewer, operations manager."""

from fastapi import APIRouter

from returnright.api.deps import AnyStaff, AuthServiceDep
from returnright.dtos.requests.auth import LoginRequest
from returnright.dtos.responses.auth import TokenResponse, UserResponse
from returnright.dtos.responses.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in and receive a JWT",
    responses={401: {"model": ErrorResponse, "description": "Wrong username or password"}},
)
def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    return service.login(payload.username, payload.password)


@router.get("/me", response_model=UserResponse, summary="The signed-in user and role")
def me(user: AnyStaff) -> UserResponse:
    return UserResponse(user_id=user.user_id, username=user.username, role=user.role)
