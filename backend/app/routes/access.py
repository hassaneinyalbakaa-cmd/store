from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..dependencies import require_permission
from ..models import Permission, Role, User
from ..schemas import Permission as PermissionSchema
from ..schemas import Role as RoleSchema
from ..serializers import to_role

router = APIRouter(tags=["access"])


@router.get("/roles", response_model=list[RoleSchema])
async def list_roles(
    _: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
) -> list[RoleSchema]:
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.id)
    )
    return [to_role(role) for role in result.scalars().all()]


@router.get("/permissions", response_model=list[PermissionSchema])
async def list_permissions(
    _: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionSchema]:
    result = await db.execute(select(Permission).order_by(Permission.id))
    return [
        PermissionSchema(
            code=permission.code,
            display_name=permission.display_name,
            description=permission.description,
        )
        for permission in result.scalars().all()
    ]
