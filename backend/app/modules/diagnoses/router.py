import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.diagnoses import service
from app.shared.voiding import VoidRequest
from app.modules.diagnoses.schemas import DiagnosisCreate, DiagnosisOut

router = APIRouter(prefix="/api/v1/patients/{patient_id}/diagnoses", tags=["diagnoses"])


@router.get("", response_model=list[DiagnosisOut])
async def get_diagnoses(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("diagnoses:read")),
):
    return await service.list_diagnoses(db, current_user.clinic_id, patient_id)


@router.post("", response_model=DiagnosisOut, status_code=201)
async def post_diagnosis(
    patient_id: uuid.UUID,
    payload: DiagnosisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("diagnoses:write")),
):
    diagnosis = await service.create_diagnosis(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return diagnosis


@router.post("/{record_id}/void", response_model=DiagnosisOut)
async def void_diagnosis(
    patient_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: VoidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("diagnoses:write")),
):
    record = await service.void_diagnosis(
        db, current_user.clinic_id, current_user.id, patient_id, record_id, payload.reason
    )
    await db.commit()
    return record
