from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..dependencies import require_permission
from ..models import Role, User
from ..schemas import User as UserSchema
from ..schemas import UserInput, UserUpdate
from ..security import hash_password
from ..serializers import to_user

router = APIRouter(prefix="/users", tags=["users"])


async def find_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def ensure_role(db: AsyncSession, role_id: int) -> Role:
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=400, detail="الدور المحدد غير موجود")
    return role


@router.get("", response_model=list[UserSchema])
async def list_users(
    _: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
) -> list[UserSchema]:
    result = await db.execute(
        select(User).options(selectinload(User.role)).order_by(User.id)
    )
    return [to_user(user) for user in result.scalars().all()]


@router.post("", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserInput,
    _: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    await ensure_role(db, payload.role_id)
    user = User(
        username=payload.username.strip().lower(),
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="اسم المستخدم مستخدم مسبقًا")
    saved = await find_user(db, user.id)
    return to_user(saved)


@router.patch("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    user = await find_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if payload.role_id is not None:
        await ensure_role(db, payload.role_id)
        user.role_id = payload.role_id
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    saved = await find_user(db, user.id)
    return to_user(saved)
