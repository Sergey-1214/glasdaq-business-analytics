from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories.user_auth import UserAuthRepository


def test_get_user_by_id_returns_scalar_result(run, session_mock, make_user):
    expected_user = make_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected_user
    session_mock.execute.return_value = result
    repo = UserAuthRepository(session_mock)

    resolved_user = run(repo.get_user_by_id(expected_user.id))

    assert resolved_user is expected_user
    session_mock.execute.assert_awaited_once()
    result.scalar_one_or_none.assert_called_once()


def test_get_user_by_email_returns_scalar_result(run, session_mock, make_user):
    expected_user = make_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected_user
    session_mock.execute.return_value = result
    repo = UserAuthRepository(session_mock)

    resolved_user = run(repo.get_user_by_email(expected_user.email))

    assert resolved_user is expected_user
    session_mock.execute.assert_awaited_once()
    result.scalar_one_or_none.assert_called_once()


def test_get_user_by_username_returns_scalar_result(run, session_mock, make_user):
    expected_user = make_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected_user
    session_mock.execute.return_value = result
    repo = UserAuthRepository(session_mock)

    resolved_user = run(repo.get_user_by_username(expected_user.username))

    assert resolved_user is expected_user
    session_mock.execute.assert_awaited_once()
    result.scalar_one_or_none.assert_called_once()


def test_add_user_adds_entity_to_session(session_mock, make_user):
    repo = UserAuthRepository(session_mock)
    user = make_user()

    repo.add_user(user)

    session_mock.add.assert_called_once_with(user)


def test_delete_user_deletes_entity_from_session(run, session_mock, make_user):
    repo = UserAuthRepository(session_mock)
    user = make_user()

    run(repo.delete_user(user))

    session_mock.delete.assert_awaited_once_with(user)


def test_add_refresh_token_adds_token_and_flushes(run, session_mock):
    repo = UserAuthRepository(session_mock)
    user_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    token = run(repo.add_refresh_token(user_id=user_id, token_hash="token-hash", expires_at=expires_at))

    assert token.user_id == user_id
    assert token.token_hash == "token-hash"
    assert token.expires_at == expires_at
    session_mock.add.assert_called_once_with(token)
    session_mock.flush.assert_awaited_once()


def test_get_refresh_token_returns_scalar_result(run, session_mock, make_refresh_token):
    expected_token = make_refresh_token(
        user_id=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected_token
    session_mock.execute.return_value = result
    repo = UserAuthRepository(session_mock)

    resolved_token = run(repo.get_refresh_token("token-hash"))

    assert resolved_token is expected_token
    session_mock.execute.assert_awaited_once()
    result.scalar_one_or_none.assert_called_once()


def test_revoke_refresh_token_updates_entity_and_flushes(run, session_mock, make_refresh_token):
    repo = UserAuthRepository(session_mock)
    revoked_at = datetime.now(timezone.utc)
    token = make_refresh_token(
        user_id=uuid4(),
        expires_at=revoked_at + timedelta(days=1),
    )

    run(repo.revoke_refresh_token(token, revoked_at))

    assert token.revoked_at == revoked_at
    session_mock.flush.assert_awaited_once()
