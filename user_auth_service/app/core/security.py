import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str, username: str) -> tuple[str, int]:
    now = utcnow()
    expires_in = settings.access_token_expire_minutes * 60
    payload = {
        "sub": user_id,
        "username": username,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def create_refresh_token() -> tuple[str, int, datetime]:
    token = secrets.token_urlsafe(48)
    expires_in = settings.refresh_token_expire_days * 24 * 60 * 60
    expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)
    return token, expires_in, expires_at


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
