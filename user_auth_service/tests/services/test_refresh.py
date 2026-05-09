from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.errors import InvalidRefreshTokenError, RefreshTokenExpiredError
from app.schemas import RefreshRequest
from app.services import user_auth as user_auth_module
from app.services.user_auth import UserAuthService


def test_refresh_raises_when_token_is_missing_or_revoked(run, session_mock, repo_mock):
    service = UserAuthService(session_mock, repo_mock)
    payload = RefreshRequest(refresh_token="some-refresh-token-value")

    with pytest.raises(InvalidRefreshTokenError):
        run(service.refresh(payload))

    session_mock.commit.assert_not_called()


def test_refresh_raises_when_token_is_expired(run, session_mock, repo_mock, make_user, make_refresh_token, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    user = make_user()
    repo_mock.get_refresh_token.return_value = make_refresh_token(
        user_id=user.id,
        expires_at=now - timedelta(seconds=1),
    )
    monkeypatch.setattr(user_auth_module, "utcnow", lambda: now)

    service = UserAuthService(session_mock, repo_mock)
    payload = RefreshRequest(refresh_token="some-refresh-token-value")

    with pytest.raises(RefreshTokenExpiredError):
        run(service.refresh(payload))

    session_mock.commit.assert_not_called()


def test_refresh_revokes_old_token_issues_new_and_commits(
    run,
    session_mock,
    repo_mock,
    make_user,
    make_refresh_token,
    monkeypatch,
):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    user = make_user()
    stored_token = make_refresh_token(
        user_id=user.id,
        expires_at=now + timedelta(days=1),
    )
    repo_mock.get_refresh_token.return_value = stored_token
    repo_mock.get_user_by_id.return_value = user
    monkeypatch.setattr(user_auth_module, "utcnow", lambda: now)

    service = UserAuthService(session_mock, repo_mock)
    service._issue_tokens = AsyncMock(return_value="new-auth-response")
    payload = RefreshRequest(refresh_token="some-refresh-token-value")

    response = run(service.refresh(payload))

    assert response == "new-auth-response"
    repo_mock.revoke_refresh_token.assert_awaited_once_with(stored_token, now)
    session_mock.commit.assert_awaited_once()
