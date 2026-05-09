from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories import UserAuthRepository
from app.schemas import MessageResponse, UpdateMeRequest, UserResponse
from app.services import UserAuthService

router = APIRouter(tags=["users"])
security = HTTPBearer()


def get_user_service(
    session: AsyncSession = Depends(get_session),
) -> UserAuthService:
    return UserAuthService(session, UserAuthRepository(session))


UserServiceDep = Annotated[UserAuthService, Depends(get_user_service)]


def extract_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="invalid authorization header")
    return credentials.credentials


BearerTokenDep = Annotated[str, Depends(extract_bearer_token)]


@router.get("/auth/me", response_model=UserResponse)
async def me(token: BearerTokenDep, service: UserServiceDep) -> UserResponse:
    return await service.me(token)


@router.patch("/users/me", response_model=UserResponse)
async def update_me(
    payload: UpdateMeRequest,
    token: BearerTokenDep,
    service: UserServiceDep,
) -> UserResponse:
    return await service.update_me(token, payload)


@router.delete("/users/me", response_model=MessageResponse)
async def delete_me(token: BearerTokenDep, service: UserServiceDep) -> MessageResponse:
    return await service.delete_me(token)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: UUID, service: UserServiceDep) -> UserResponse:
    return await service.get_user_by_id(user_id)


@router.get("/users/by-username/{username}", response_model=UserResponse)
async def get_user_by_username(username: str, service: UserServiceDep) -> UserResponse:
    return await service.get_user_by_username(username)
