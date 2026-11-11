from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.shared.config import settings


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Raises JWTError if the token is invalid, expired, or tampered.
    Returns the payload dict on success.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


def check_role(token: str, allowed_roles: list[str]) -> dict[str, Any]:
    """
    Decode the token and ensure its 'role' claim is in allowed_roles.
    Raises JWTError if invalid/expired, PermissionError if role not allowed.
    """
    payload = decode_access_token(token)
    if payload.get("role") not in allowed_roles:
        raise PermissionError("Insufficient permissions")
    return payload