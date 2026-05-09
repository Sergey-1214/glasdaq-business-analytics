from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories import UserAuthRepository
from app.schemas import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
)
from app.services import UserAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> UserAuthService:
    return UserAuthService(session, UserAuthRepository(session))


AuthServiceDep = Annotated[UserAuthService, Depends(get_auth_service)]


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> AuthResponse:
    return await service.register(payload)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, service: AuthServiceDep) -> AuthResponse:
    return await service.login(payload)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> AuthResponse:
    return await service.refresh(payload)


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: LogoutRequest, service: AuthServiceDep) -> MessageResponse:
    return await service.logout(payload.refresh_token)
