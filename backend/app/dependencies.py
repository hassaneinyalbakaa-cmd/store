from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_db
from .models import User
from .security import get_session_user


async def current_user(
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Cookie(
        default=None, alias=get_settings().session_cookie_name
    ),
) -> User:
    user = await get_session_user(db, session_token)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="يجب تسجيل الدخول للمتابعة",
        )
    return user


def require_permission(permission: str):
    async def dependency(user: User = Depends(current_user)) -> User:
        if not user.role or permission not in {item.code for item in user.role.permissions}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="لا تملك الصلاحية لتنفيذ هذا الإجراء",
            )
        return user

    return dependency


async def admin_user(user: User = Depends(current_user)) -> User:
    if not user.role or user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء متاح لمدير النظام فقط",
        )
    return user


def require_admin():
    return admin_user
