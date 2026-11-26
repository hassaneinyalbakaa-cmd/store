"""Operator-authorized, once-only recovery; never exposed as an HTTP endpoint."""

import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import add_audit_log
from .config import Settings
from .db import SessionLocal
from .models import AuditLog, User, UserSession
from .security import hash_password

logger = logging.getLogger(__name__)
RESET_ACTION = "admin_password_reset_once"


async def apply_admin_password_reset(
    db: AsyncSession, *, request_id: str, password: str | None
) -> bool:
    """Run inside the caller's transaction; lock prevents concurrent resets."""
    try:
        request_id = str(UUID(request_id))
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError("ADMIN_RESET_REQUEST_ID must be a valid UUID.") from None

    result = await db.execute(
        select(User).where(User.username == "admin").with_for_update(of=User)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.role.name != "admin":
        raise RuntimeError("Recovery requires an existing active admin account.")

    # Check after taking the account lock. Another startup may have just
    # committed this request. Never overwrite later user password changes.
    result = await db.execute(
        select(AuditLog.id)
        .where(
            AuditLog.user_id == user.id,
            AuditLog.action == RESET_ACTION,
            AuditLog.document_number == request_id,
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return False

    if not password or len(password) < 12 or not password.strip():
        raise RuntimeError("ADMIN_RESET_PASSWORD must contain at least 12 characters.")

    user.password_hash = hash_password(password)
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    add_audit_log(
        db,
        user=user,
        action=RESET_ACTION,
        document_number=request_id,
        details="إعادة تعيين كلمة مرور المدير بموافقة المالك وإلغاء الجلسات السابقة",
    )
    return True


async def recover_admin_on_startup(settings: Settings) -> None:
    """Only an explicit production request can enable this maintenance action."""
    if settings.environment != "production" or not settings.admin_reset_request_id:
        return

    password = (
        settings.admin_reset_password.get_secret_value()
        if settings.admin_reset_password
        else None
    )
    async with SessionLocal() as db:
        async with db.begin():
            changed = await apply_admin_password_reset(
                db, request_id=settings.admin_reset_request_id, password=password
            )
    logger.info(
        "Authorized admin recovery applied; prior sessions revoked."
        if changed
        else "Admin recovery request already applied; account left unchanged."
    )
