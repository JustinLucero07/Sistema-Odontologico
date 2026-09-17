import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.medical_history import service
from app.modules.medical_history.schemas import MedicalHistoryCreate, MedicalHistoryOut

router = APIRouter(prefix="/api/v1/patients/{patient_id}/medical-history", tags=["medical-history"])


@router.get("", response_model=MedicalHistoryOut | None)
async def get_latest_medical_history(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:read")),
):
    return await service.get_latest(db, current_user.clinic_id, patient_id)


@router.get("/versions", response_model=list[MedicalHistoryOut])
async def get_medical_history_versions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:read")),
):
    return await service.list_versions(db, current_user.clinic_id, patient_id)


@router.post("", response_model=MedicalHistoryOut, status_code=201)
async def post_medical_history(
    patient_id: uuid.UUID,
    payload: MedicalHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:write")),
):
    entry = await service.create_version(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return entry
