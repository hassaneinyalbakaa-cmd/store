from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    message: str


class LoginInput(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class SessionUser(BaseModel):
    id: int
    username: str
    display_name: str
    role_id: int
    role_name: str
    permissions: list[str]
    is_active: bool


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role_id: int
    role_name: str
    is_active: bool
    created_at: datetime


class UserInput(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)
    role_id: int
    is_active: bool = True


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    role_id: int | None = None
    is_active: bool | None = None


class Role(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    permissions: list[str]


class Permission(BaseModel):
    code: str
    display_name: str
    description: str


class DashboardSummary(BaseModel):
    users_total: int
    active_users: int
    roles_total: int
    permissions_total: int
