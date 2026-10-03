import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.insights import service
from app.modules.insights.schemas import FreeSlot, Opportunities

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("/opportunities", response_model=Opportunities)
async def get_opportunities(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    """A quién llamar hoy y por qué. Los deudores solo aparecen para quien
    puede ver los cobros."""
    can_money = current_user.is_superadmin or "payments:read" in current_user.permissions
    return await service.opportunities(db, current_user.clinic_id, can_money)


@router.get("/free-slots", response_model=list[FreeSlot])
async def get_free_slots(
    professional_id: uuid.UUID,
    duration: int = Query(default=30, ge=10, le=240),
    date_from: date | None = None,
    days: int = Query(default=7, ge=1, le=31),
    limit: int = Query(default=12, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return await service.free_slots(db, current_user.clinic_id, professional_id, duration, date_from, days, limit)
