from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import EmailAlreadyExistsError
from app.schemas import RegisterRequest
from app.services.user_auth import UserAuthService


def test_register_success_normalizes_email_and_commits(run, session_mock, repo_mock):
    service = UserAuthService(session_mock, repo_mock)
    payload = RegisterRequest(
        username="  John  ",
        email="JOHN@EXAMPLE.COM",
        password="secret123",
    )
    expected_response = object()
    service._issue_tokens = AsyncMock(return_value=expected_response)

    run(service.register(payload))

    added_user = repo_mock.add_user.call_args.args[0]
    assert added_user.username == "John"
    assert added_user.email == "john@example.com"
    assert added_user.password_hash != payload.password
    session_mock.flush.assert_awaited_once()
    session_mock.commit.assert_awaited_once()


def test_register_rolls_back_on_integrity_error(run, session_mock, repo_mock):
    service = UserAuthService(session_mock, repo_mock)
    payload = RegisterRequest(
        username="john",
        email="john@example.com",
        password="secret123",
    )
    session_mock.flush.side_effect = IntegrityError("insert", {}, Exception("duplicate key"))

    with pytest.raises(EmailAlreadyExistsError):
        run(service.register(payload))

    session_mock.rollback.assert_awaited_once()
    session_mock.commit.assert_not_called()
