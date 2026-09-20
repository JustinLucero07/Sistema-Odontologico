import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.prescriptions import service
from app.modules.prescriptions.schemas import PrescriptionCreate, PrescriptionOut

router = APIRouter(prefix="/api/v1/patients/{patient_id}/prescriptions", tags=["prescriptions"])


@router.get("", response_model=list[PrescriptionOut])
async def get_prescriptions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("prescriptions:read")),
):
    return await service.list_prescriptions(db, current_user.clinic_id, patient_id)


@router.post("", response_model=PrescriptionOut, status_code=201)
async def post_prescription(
    patient_id: uuid.UUID,
    payload: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("prescriptions:write")),
):
    prescription = await service.create_prescription(
        db, current_user.clinic_id, current_user.id, patient_id, payload
    )
    await db.commit()
    return prescription
