import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.odontogram import service
from app.modules.odontogram.schemas import OdontogramCreate, OdontogramOut, OdontogramSummary

router = APIRouter(prefix="/api/v1/patients/{patient_id}/odontogram", tags=["odontogram"])


@router.get("", response_model=OdontogramOut | None)
async def get_latest_odontogram(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("odontogram:read")),
):
    return await service.get_latest(db, current_user.clinic_id, patient_id)


@router.get("/versions", response_model=list[OdontogramSummary])
async def get_odontogram_versions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("odontogram:read")),
):
    return await service.list_versions(db, current_user.clinic_id, patient_id)


@router.get("/{odontogram_id}", response_model=OdontogramOut)
async def get_odontogram_version(
    patient_id: uuid.UUID,
    odontogram_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("odontogram:read")),
):
    odontogram = await service.get_version(db, current_user.clinic_id, patient_id, odontogram_id)
    if odontogram is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Odontograma no encontrado")
    return odontogram


@router.post("", response_model=OdontogramOut, status_code=201)
async def post_odontogram(
    patient_id: uuid.UUID,
    payload: OdontogramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("odontogram:write")),
):
    odontogram = await service.create_snapshot(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return odontogram
