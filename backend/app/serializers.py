from .models import Department, Item, Role, StorageLocation, User, Warehouse
from .schemas import Role as RoleSchema
from .schemas import (
    Department as DepartmentSchema,
    Item as ItemSchema,
    SessionUser,
    StorageLocation as StorageLocationSchema,
    User as UserSchema,
    Warehouse as WarehouseSchema,
)


def to_session_user(user: User) -> SessionUser:
    return SessionUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_id=user.role_id,
        role_name=user.role.display_name,
        permissions=sorted(permission.code for permission in user.role.permissions),
        is_active=user.is_active,
    )


def to_user(user: User) -> UserSchema:
    return UserSchema(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_id=user.role_id,
        role_name=user.role.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def to_role(role: Role) -> RoleSchema:
    return RoleSchema(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        permissions=sorted(permission.code for permission in role.permissions),
    )


def to_warehouse(warehouse: Warehouse) -> WarehouseSchema:
    return WarehouseSchema(
        id=warehouse.id,
        name=warehouse.name,
        code=warehouse.code,
        description=warehouse.description,
        warehouse_type=warehouse.warehouse_type,
        is_active=warehouse.is_active,
    )


def to_department(department: Department) -> DepartmentSchema:
    return DepartmentSchema(
        id=department.id,
        name=department.name,
        code=department.code,
        is_active=department.is_active,
    )


def to_storage_location(location: StorageLocation | None) -> StorageLocationSchema | None:
    if location is None:
        return None
    return StorageLocationSchema(
        id=location.id,
        warehouse_id=location.warehouse_id,
        area=location.area,
        shelf=location.shelf,
        bin=location.bin,
    )


def to_item(item: Item) -> ItemSchema:
    return ItemSchema(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        category=item.category,
        unit=item.unit,
        part_number=item.part_number,
        minimum_level=item.minimum_level,
        warehouse_id=item.warehouse_id,
        warehouse_name=item.warehouse.name,
        storage_location=to_storage_location(item.storage_location),
        requires_serial_number=item.requires_serial_number,
        requires_expiry_date=item.requires_expiry_date,
        is_active=item.is_active,
        created_at=item.created_at,
    )
