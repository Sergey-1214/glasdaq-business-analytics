from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.errors import EmailAlreadyExistsError, EmptyUpdateError, InvalidTokenError
from app.schemas import UpdateMeRequest
from app.services import user_auth as user_auth_module
from app.services.user_auth import UserAuthService


def test_update_me_raises_on_empty_payload(run, session_mock, repo_mock, make_user):
    service = UserAuthService(session_mock, repo_mock)
    service._resolve_user_from_access_token = AsyncMock(return_value=make_user())

    with pytest.raises(EmptyUpdateError):
        run(service.update_me("token", UpdateMeRequest()))

    session_mock.commit.assert_not_called()


def test_update_me_raises_on_email_conflict(run, session_mock, repo_mock, make_user):
    user = make_user()
    conflict_user = make_user(email="taken@example.com")
    repo_mock.get_user_by_email.return_value = conflict_user
    service = UserAuthService(session_mock, repo_mock)
    service._resolve_user_from_access_token = AsyncMock(return_value=user)

    with pytest.raises(EmailAlreadyExistsError):
        run(service.update_me("token", UpdateMeRequest(email="taken@example.com")))

    session_mock.commit.assert_not_called()


def test_logout_revokes_token_and_commits(run, session_mock, repo_mock, make_refresh_token, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    token = make_refresh_token(user_id=uuid4(), expires_at=now + timedelta(days=1))
    repo_mock.get_refresh_token.return_value = token
    monkeypatch.setattr(user_auth_module, "utcnow", lambda: now)

    service = UserAuthService(session_mock, repo_mock)
    response = run(service.logout("refresh-token-value"))

    assert response.data == {"revoked": True}
    repo_mock.revoke_refresh_token.assert_awaited_once_with(token, now)
    session_mock.commit.assert_awaited_once()


def test_resolve_user_from_access_token_raises_on_invalid_token(run, session_mock, repo_mock, monkeypatch):
    monkeypatch.setattr(user_auth_module.jwt, "decode", lambda *args, **kwargs: {})
    service = UserAuthService(session_mock, repo_mock)

    with pytest.raises(InvalidTokenError):
        run(service._resolve_user_from_access_token("invalid"))


def test_resolve_user_from_access_token_returns_user(run, session_mock, repo_mock, make_user, monkeypatch):
    user = make_user()
    repo_mock.get_user_by_id.return_value = user
    monkeypatch.setattr(user_auth_module.jwt, "decode", lambda *args, **kwargs: {"sub": str(user.id)})
    service = UserAuthService(session_mock, repo_mock)

    resolved_user = run(service._resolve_user_from_access_token("valid"))

    assert resolved_user is user
