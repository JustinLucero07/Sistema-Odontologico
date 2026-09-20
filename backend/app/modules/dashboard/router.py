from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.dashboard import service
from app.modules.dashboard.schemas import DashboardSummary

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    days: int = Query(default=7, ge=1, le=31),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Available to any signed-in user: it only exposes counts for their own
    clinic, and the UI hides the cards a role has no business seeing."""
    return await service.build_summary(db, current_user.clinic_id, days)
