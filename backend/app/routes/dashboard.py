from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..dependencies import current_user
from ..models import Permission, Role, User
from ..schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> DashboardSummary:
    users_total = await db.scalar(select(func.count()).select_from(User))
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    roles_total = await db.scalar(select(func.count()).select_from(Role))
    permissions_total = await db.scalar(select(func.count()).select_from(Permission))
    return DashboardSummary(
        users_total=users_total or 0,
        active_users=active_users or 0,
        roles_total=roles_total or 0,
        permissions_total=permissions_total or 0,
    )
