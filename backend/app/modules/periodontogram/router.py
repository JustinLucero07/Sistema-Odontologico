import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.periodontogram import service
from app.modules.periodontogram.constants import PERIODONTAL_SITES
from app.modules.periodontogram.schemas import (
    PeriodontogramCreate,
    PeriodontogramOut,
    PeriodontogramSummary,
)

router = APIRouter(prefix="/api/v1/patients/{patient_id}/periodontogram", tags=["periodontogram"])
catalog_router = APIRouter(prefix="/api/v1/periodontogram", tags=["periodontogram"])


@catalog_router.get("/sites")
async def get_sites(
    current_user: CurrentUser = Depends(require_permission("periodontogram:read")),
):
    return [{"code": code, "label": label} for code, label in PERIODONTAL_SITES]


@router.get("", response_model=PeriodontogramOut | None)
async def get_latest_periodontogram(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("periodontogram:read")),
):
    return await service.get_latest(db, current_user.clinic_id, patient_id)


@router.get("/versions", response_model=list[PeriodontogramSummary])
async def get_periodontogram_versions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("periodontogram:read")),
):
    return await service.list_versions(db, current_user.clinic_id, patient_id)


@router.get("/{periodontogram_id}", response_model=PeriodontogramOut)
async def get_periodontogram_version(
    patient_id: uuid.UUID,
    periodontogram_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("periodontogram:read")),
):
    periodontogram = await service.get_version(
        db, current_user.clinic_id, patient_id, periodontogram_id
    )
    if periodontogram is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Periodontograma no encontrado"
        )
    return periodontogram


@router.post("", response_model=PeriodontogramOut, status_code=201)
async def post_periodontogram(
    patient_id: uuid.UUID,
    payload: PeriodontogramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("periodontogram:write")),
):
    periodontogram = await service.create_snapshot(
        db, current_user.clinic_id, current_user.id, patient_id, payload
    )
    await db.commit()
    return periodontogram
