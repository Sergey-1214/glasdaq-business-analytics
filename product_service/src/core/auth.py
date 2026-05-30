from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.exceptions import AuthError


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID


security = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "change_me_please")


def _jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _jwt_issuer() -> str:
    return os.getenv("JWT_ISSUER", "user_auth_service")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthError("Missing or invalid authorization header")

    try:
        payload = jwt.decode(
            credentials.credentials,
            _jwt_secret(),
            algorithms=[_jwt_algorithm()],
            issuer=_jwt_issuer(),
        )
    except Exception as exc:
        raise AuthError(f"Invalid access token: {exc}") from exc

    subject = payload.get("sub")
    if not subject:
        raise AuthError("Access token does not contain subject")

    try:
        return CurrentUser(user_id=UUID(subject))
    except ValueError as exc:
        raise AuthError("Invalid subject in access token") from exc
