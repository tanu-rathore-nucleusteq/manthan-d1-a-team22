"""Staff sign-in: checks the password and issues a JWT carrying the user's role."""

from returnright.core.config import Settings
from returnright.core.exceptions import InvalidCredentialsError
from returnright.core.security import create_access_token, unknown_user_hash, verify_password
from returnright.dtos.internal.auth import CurrentUser
from returnright.dtos.responses.auth import TokenResponse
from returnright.repositories.user_repository import StaffUserRepository
from returnright.utils.clock import Clock


class AuthService:
    def __init__(self, users: StaffUserRepository, settings: Settings, clock: Clock) -> None:
        self._users = users
        self._settings = settings
        self._clock = clock

    def login(self, username: str, password: str) -> TokenResponse:
        user = self._users.find_active_by_login(username)
        if user is None:
            verify_password(password, unknown_user_hash())
            raise InvalidCredentialsError()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        current = CurrentUser(user_id=user.staff_id, username=user.username, role=user.role)
        return TokenResponse(
            access_token=create_access_token(current, self._settings, self._clock.now()),
            expires_in=self._settings.jwt_expire_minutes * 60,
            role=user.role,
        )
