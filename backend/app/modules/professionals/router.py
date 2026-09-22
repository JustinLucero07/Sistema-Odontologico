import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.professionals import service
from app.modules.professionals.schemas import (
    ProfessionalCreate,
    ProfessionalOut,
    ProfessionalUpdate,
    SpecialtyCreate,
    SpecialtyOut,
    SpecialtyUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["professionals"])


@router.get("/specialties", response_model=list[SpecialtyOut])
async def get_specialties(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    return await service.list_specialties(db, current_user.clinic_id)


@router.post("/specialties", response_model=SpecialtyOut, status_code=201)
async def post_specialty(
    payload: SpecialtyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    specialty = await service.create_specialty(db, current_user.clinic_id, payload)
    await db.commit()
    return specialty


@router.put("/specialties/{specialty_id}", response_model=SpecialtyOut)
async def put_specialty(
    specialty_id: uuid.UUID,
    payload: SpecialtyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    specialty = await service.update_specialty(db, current_user.clinic_id, specialty_id, payload)
    await db.commit()
    return specialty


@router.delete("/specialties/{specialty_id}", status_code=204)
async def delete_specialty(
    specialty_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    await service.delete_specialty(db, current_user.clinic_id, specialty_id)
    await db.commit()


@router.get("/professionals", response_model=list[ProfessionalOut])
async def get_professionals(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return await service.list_professionals(db, current_user.clinic_id)


@router.post("/professionals", response_model=ProfessionalOut, status_code=201)
async def post_professional(
    payload: ProfessionalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    professional = await service.create_professional(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return professional


@router.put("/professionals/{professional_id}", response_model=ProfessionalOut)
async def put_professional(
    professional_id: uuid.UUID,
    payload: ProfessionalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    professional = await service.update_professional(
        db, current_user.clinic_id, current_user.id, professional_id, payload
    )
    await db.commit()
    return professional
