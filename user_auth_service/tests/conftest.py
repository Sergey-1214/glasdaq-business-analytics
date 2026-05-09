import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.models import RefreshToken, User


@pytest.fixture
def run():
    def _run(coro):
        return asyncio.run(coro)

    return _run


@pytest.fixture
def make_user():
    def _make_user(
        *,
        username: str = "john",
        email: str = "john@example.com",
        password_hash: str = "hashed-password",
        is_active: bool = True,
    ) -> User:
        now = datetime.now(timezone.utc)
        user = User(username=username, email=email, password_hash=password_hash)
        user.id = uuid4()
        user.is_active = is_active
        user.created_at = now
        user.updated_at = now
        user.last_login_at = None
        return user

    return _make_user


@pytest.fixture
def make_refresh_token():
    def _make_refresh_token(
        *,
        user_id,
        expires_at: datetime,
        revoked_at: datetime | None = None,
    ) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash="token-hash", expires_at=expires_at)
        token.revoked_at = revoked_at
        return token

    return _make_refresh_token


@pytest.fixture
def session_mock():
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def repo_mock():
    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=None)
    repo.get_user_by_username = AsyncMock(return_value=None)
    repo.get_user_by_id = AsyncMock(return_value=None)
    repo.get_refresh_token = AsyncMock(return_value=None)
    repo.revoke_refresh_token = AsyncMock()
    repo.delete_user = AsyncMock()
    repo.add_refresh_token = AsyncMock()
    return repo
