from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..audit import add_audit_log
from ..db import get_db
from ..dependencies import current_user
from ..models import Role, User
from ..schemas import LoginInput, MessageResponse, SessionUser
from ..security import create_session, delete_session, verify_password
from ..serializers import to_session_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SessionUser)
async def login(
    payload: LoginInput, response: Response, db: AsyncSession = Depends(get_db)
) -> SessionUser:
    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.username == payload.username.strip().lower())
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        add_audit_log(
            db,
            user=None,
            action="login_failed",
            details=f"اسم المستخدم: {payload.username.strip().lower()[:80]}",
            username=payload.username.strip().lower()[:80],
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة",
        )

    token = await create_session(db, user)
    add_audit_log(db, user=user, action="login", details="تم إنشاء جلسة جديدة")
    await db.commit()
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
    )
    return to_session_user(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Cookie(
        default=None, alias=get_settings().session_cookie_name
    ),
) -> MessageResponse:
    await delete_session(db, session_token)
    response.delete_cookie(key=get_settings().session_cookie_name, path="/")
    return MessageResponse(message="تم تسجيل الخروج بنجاح")


@router.get("/me", response_model=SessionUser)
async def get_current_user(user: User = Depends(current_user)) -> SessionUser:
    return to_session_user(user)
