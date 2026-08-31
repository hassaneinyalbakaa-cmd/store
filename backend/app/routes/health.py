from fastapi import APIRouter

from ..schemas import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    return HealthStatus(status="ok")
