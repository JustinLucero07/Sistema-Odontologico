import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.clinical_evolution import service
from app.modules.clinical_evolution.schemas import EvolutionCreate, EvolutionOut, EvolutionUpdate

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/evolutions", tags=["evolutions"])
router = APIRouter(prefix="/api/v1/evolutions", tags=["evolutions"])


@patient_router.get("", response_model=list[EvolutionOut])
async def get_evolutions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evolutions:read")),
):
    return await service.list_evolutions(db, current_user.clinic_id, patient_id)


@patient_router.post("", response_model=EvolutionOut, status_code=201)
async def post_evolution(
    patient_id: uuid.UUID,
    payload: EvolutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evolutions:write")),
):
    entry = await service.create_evolution(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return entry


@router.put("/{evolution_id}", response_model=EvolutionOut)
async def put_evolution(
    evolution_id: uuid.UUID,
    payload: EvolutionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evolutions:write")),
):
    entry = await service.update_evolution(db, current_user.clinic_id, current_user.id, evolution_id, payload)
    await db.commit()
    return entry
