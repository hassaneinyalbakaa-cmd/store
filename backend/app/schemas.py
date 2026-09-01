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


class Warehouse(BaseModel):
    id: int
    name: str
    code: str
    description: str
    warehouse_type: str
    is_active: bool


class WarehouseInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=255)
    warehouse_type: str = Field(default="branch", pattern="^(main|branch)$")
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=255)
    warehouse_type: str | None = Field(default=None, pattern="^(main|branch)$")
    is_active: bool | None = None


class Department(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool


class DepartmentInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool | None = None


class StorageLocation(BaseModel):
    id: int
    warehouse_id: int
    area: str
    shelf: str
    bin: str


class StorageLocationInput(BaseModel):
    area: str = Field(min_length=1, max_length=80)
    shelf: str = Field(min_length=1, max_length=80)
    bin: str = Field(min_length=1, max_length=80)


class Item(BaseModel):
    id: int
    code: str
    name: str
    description: str
    category: str
    unit: str
    part_number: str | None
    minimum_level: float
    warehouse_id: int
    warehouse_name: str
    storage_location: StorageLocation | None
    requires_serial_number: bool
    requires_expiry_date: bool
    is_active: bool
    created_at: datetime


class ItemInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=255)
    category: str = Field(default="", max_length=120)
    unit: str = Field(min_length=1, max_length=60)
    part_number: str | None = Field(default=None, max_length=120)
    minimum_level: float = Field(default=0, ge=0)
    warehouse_id: int
    storage_location: StorageLocationInput | None = None
    requires_serial_number: bool = False
    requires_expiry_date: bool = False
    is_active: bool = True


class ItemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, min_length=1, max_length=60)
    part_number: str | None = Field(default=None, max_length=120)
    minimum_level: float | None = Field(default=None, ge=0)
    warehouse_id: int | None = None
    storage_location: StorageLocationInput | None = None
    requires_serial_number: bool | None = None
    requires_expiry_date: bool | None = None
    is_active: bool | None = None
