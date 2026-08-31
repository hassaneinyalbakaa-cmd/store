from .models import Role, User
from .schemas import Role as RoleSchema
from .schemas import SessionUser, User as UserSchema


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
