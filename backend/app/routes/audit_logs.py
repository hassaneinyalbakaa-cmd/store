from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..dependencies import require_permission
from ..models import AuditLog, User
from ..schemas import AuditLog as AuditLogSchema
from ..serializers import to_audit_log

router = APIRouter(tags=["audit_logs"])


@router.get("/audit-logs", response_model=list[AuditLogSchema])
async def list_audit_logs(
    search: str | None = Query(default=None, max_length=120),
    action: str | None = Query(default=None, max_length=60),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    _: User = Depends(require_permission("audit_logs:read")),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogSchema]:
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                AuditLog.username.ilike(term),
                AuditLog.user_name.ilike(term),
                AuditLog.action_label.ilike(term),
                AuditLog.document_number.ilike(term),
                AuditLog.details.ilike(term),
            )
        )
    if action:
        filters.append(AuditLog.action == action)
    if date_from:
        filters.append(
            AuditLog.created_at
            >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to:
        filters.append(
            AuditLog.created_at
            < datetime.combine(
                date.fromordinal(date_to.toordinal() + 1),
                time.min,
                tzinfo=timezone.utc,
            )
        )
    result = await db.execute(
        select(AuditLog).where(*filters).order_by(AuditLog.id.desc()).limit(limit)
    )
    return [to_audit_log(entry) for entry in result.scalars().all()]