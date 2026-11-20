"""POST /auth/login for internal roles: warehouse agent, finance reviewer, operations manager."""

from fastapi import APIRouter

from returnright.api.deps import AnyStaff, DbSession
from returnright.api.not_implemented import not_implemented
from returnright.dtos.requests.auth import LoginRequest
from returnright.dtos.responses.auth import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Sign in and receive a JWT")
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    not_implemented("Login")


@router.get("/me", response_model=UserResponse, summary="The signed-in user and role")
def me(user: AnyStaff) -> UserResponse:
    not_implemented("Current user")
