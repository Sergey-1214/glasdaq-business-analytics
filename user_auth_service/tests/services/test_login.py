from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.errors import InvalidCredentialsError
from app.schemas import LoginRequest
from app.services import user_auth as user_auth_module
from app.services.user_auth import UserAuthService


def test_login_raises_on_invalid_credentials(run, session_mock, repo_mock):
    service = UserAuthService(session_mock, repo_mock)
    payload = LoginRequest(email="john@example.com", password="bad")

    with pytest.raises(InvalidCredentialsError):
        run(service.login(payload))

    session_mock.commit.assert_not_called()


def test_login_updates_last_login_and_commits(run, session_mock, repo_mock, make_user, monkeypatch):
    user = make_user(password_hash="stored-hash")
    repo_mock.get_user_by_email.return_value = user
    monkeypatch.setattr(user_auth_module, "verify_password", lambda raw, stored: True)
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(user_auth_module, "utcnow", lambda: fixed_now)

    service = UserAuthService(session_mock, repo_mock)
    service._issue_tokens = AsyncMock(return_value="auth-response")
    payload = LoginRequest(email="USER@EXAMPLE.COM", password="secret123")

    response = run(service.login(payload))

    assert response == "auth-response"
    assert user.last_login_at == fixed_now
    repo_mock.get_user_by_email.assert_awaited_once_with("user@example.com")
    session_mock.commit.assert_awaited_once()
