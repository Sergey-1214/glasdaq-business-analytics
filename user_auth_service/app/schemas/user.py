from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UpdateMeRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class UserResponse(BaseModel):
    data: UserOut


class MessageResponse(BaseModel):
    data: dict[str, bool]
