from uuid import UUID

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    EmailAlreadyExistsError,
    EmptyUpdateError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    RefreshTokenExpiredError,
    UserNotFoundError,
    UsernameAlreadyExistsError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    utcnow,
    verify_password,
)
from app.models import User
from app.repositories import UserAuthRepository
from app.schemas import (
    AuthData,
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    UpdateMeRequest,
    UserOut,
    UserResponse,
)


class UserAuthService:
    def __init__(self, session: AsyncSession, repo: UserAuthRepository) -> None:
        self._session = session
        self._repo = repo

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        email = payload.email.strip().lower()
        username = payload.username.strip()

        if await self._repo.get_user_by_email(email):
            raise EmailAlreadyExistsError()
        if await self._repo.get_user_by_username(username):
            raise UsernameAlreadyExistsError()

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(payload.password),
        )
        self._repo.add_user(user)

        try:
            await self._session.flush()
            await self._session.refresh(user)
            auth_response = await self._issue_tokens(user)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise EmailAlreadyExistsError() from exc

        return auth_response

    async def login(self, payload: LoginRequest) -> AuthResponse:
        email = payload.email.strip().lower()
        user = await self._repo.get_user_by_email(email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InvalidCredentialsError("user is inactive")

        user.last_login_at = utcnow()
        auth_response = await self._issue_tokens(user)
        await self._session.commit()
        return auth_response

    async def refresh(self, payload: RefreshRequest) -> AuthResponse:
        token_hash = hash_refresh_token(payload.refresh_token)
        stored_token = await self._repo.get_refresh_token(token_hash)
        if not stored_token or stored_token.revoked_at is not None:
            raise InvalidRefreshTokenError()

        now = utcnow()
        if stored_token.expires_at < now:
            raise RefreshTokenExpiredError()

        await self._repo.revoke_refresh_token(stored_token, now)
        user = await self._repo.get_user_by_id(stored_token.user_id)
        if not user or not user.is_active:
            raise InvalidRefreshTokenError()

        auth_response = await self._issue_tokens(user)
        await self._session.commit()
        return auth_response

    async def logout(self, refresh_token: str) -> MessageResponse:
        token_hash = hash_refresh_token(refresh_token)
        stored_token = await self._repo.get_refresh_token(token_hash)
        if stored_token and stored_token.revoked_at is None:
            await self._repo.revoke_refresh_token(stored_token, utcnow())
            await self._session.commit()
        return MessageResponse(data={"revoked": True})

    async def me(self, access_token: str) -> UserResponse:
        user = await self._resolve_user_from_access_token(access_token)
        return UserResponse(data=await self._as_user_out(user))

    async def update_me(self, access_token: str, payload: UpdateMeRequest) -> UserResponse:
        user = await self._resolve_user_from_access_token(access_token)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise EmptyUpdateError()

        if "username" in update_data:
            new_username = update_data["username"].strip()
            existing = await self._repo.get_user_by_username(new_username)
            if existing and existing.id != user.id:
                raise UsernameAlreadyExistsError()
            user.username = new_username

        if "email" in update_data:
            new_email = update_data["email"].strip().lower()
            existing = await self._repo.get_user_by_email(new_email)
            if existing and existing.id != user.id:
                raise EmailAlreadyExistsError()
            user.email = new_email

        if "password" in update_data:
            user.password_hash = hash_password(update_data["password"])

        await self._session.commit()
        return UserResponse(data=await self._as_user_out(user))

    async def delete_me(self, access_token: str) -> MessageResponse:
        user = await self._resolve_user_from_access_token(access_token)
        await self._repo.delete_user(user)
        await self._session.commit()
        return MessageResponse(data={"deleted": True})

    async def get_user_by_id(self, user_id: UUID) -> UserResponse:
        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return UserResponse(data=await self._as_user_out(user))

    async def get_user_by_username(self, username: str) -> UserResponse:
        user = await self._repo.get_user_by_username(username.strip())
        if not user:
            raise UserNotFoundError()
        return UserResponse(data=await self._as_user_out(user))

    async def _resolve_user_from_access_token(self, access_token: str) -> User:
        try:
            payload = jwt.decode(
                access_token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except Exception as exc:
            raise InvalidTokenError() from exc

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        try:
            user_uuid = UUID(user_id)
        except ValueError as exc:
            raise InvalidTokenError() from exc

        user = await self._repo.get_user_by_id(user_uuid)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise InvalidTokenError("user is inactive")
        return user

    async def _issue_tokens(self, user: User) -> AuthResponse:
        access_token, access_expires_in = create_access_token(str(user.id), user.username)
        refresh_token, refresh_expires_in, refresh_expires_at = create_refresh_token()
        await self._repo.add_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
        )
        user_out = await self._as_user_out(user)

        return AuthResponse(
            data=AuthData(
                access_token=access_token,
                refresh_token=refresh_token,
                access_expires_in=access_expires_in,
                refresh_expires_in=refresh_expires_in,
                user=user_out,
            )
        )

    async def _as_user_out(self, user: User) -> UserOut:
        await self._session.refresh(user)
        return UserOut.model_validate(user)
