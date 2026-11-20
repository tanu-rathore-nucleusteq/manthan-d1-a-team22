"""Password hashing (bcrypt) and JWT creation and verification with a role claim."""

from datetime import datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt

from returnright.core.config import Settings
from returnright.domain.enums import Role
from returnright.dtos.internal.auth import CurrentUser


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # a malformed hash, or a password over bcrypt's 72-byte limit
        return False


@lru_cache
def unknown_user_hash() -> str:
    """Checked when the username doesn't exist, so a wrong username takes as long as a wrong
    password and logins don't reveal which usernames are real."""
    return hash_password("placeholder for unknown users")


def create_access_token(user: CurrentUser, settings: Settings, now: datetime) -> str:
    payload = {
        "sub": str(user.user_id),
        "username": user.username,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> CurrentUser:
    """Raises jwt.InvalidTokenError when the token is forged, expired or malformed."""
    claims = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "role", "exp"]},
    )
    try:
        return CurrentUser(
            user_id=int(claims["sub"]),
            username=str(claims.get("username", "")),
            role=Role(claims["role"]),
        )
    except (KeyError, ValueError) as error:
        raise jwt.InvalidTokenError("Malformed claims") from error
