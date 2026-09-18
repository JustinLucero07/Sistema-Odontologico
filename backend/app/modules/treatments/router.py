import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.treatments import service
from app.modules.treatments.schemas import TreatmentCreate, TreatmentOut, TreatmentUpdate

router = APIRouter(prefix="/api/v1/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentOut])
async def get_treatments(
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:read")),
):
    return await service.list_treatments(db, current_user.clinic_id, include_inactive)


@router.post("", response_model=TreatmentOut, status_code=201)
async def post_treatment(
    payload: TreatmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:write")),
):
    treatment = await service.create_treatment(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return treatment


@router.put("/{treatment_id}", response_model=TreatmentOut)
async def put_treatment(
    treatment_id: uuid.UUID,
    payload: TreatmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:write")),
):
    treatment = await service.update_treatment(db, current_user.clinic_id, current_user.id, treatment_id, payload)
    await db.commit()
    return treatment
