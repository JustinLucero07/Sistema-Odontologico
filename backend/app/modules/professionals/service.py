import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.professionals.models import Professional, Specialty
from app.modules.professionals.schemas import ProfessionalCreate, ProfessionalUpdate, SpecialtyCreate


async def list_specialties(db: AsyncSession, clinic_id: uuid.UUID) -> list[Specialty]:
    result = await db.execute(select(Specialty).where(Specialty.clinic_id == clinic_id).order_by(Specialty.name))
    return list(result.scalars().all())


async def create_specialty(db: AsyncSession, clinic_id: uuid.UUID, payload: SpecialtyCreate) -> Specialty:
    specialty = Specialty(clinic_id=clinic_id, name=payload.name)
    db.add(specialty)
    await db.flush()
    return specialty


async def list_professionals(db: AsyncSession, clinic_id: uuid.UUID) -> list[Professional]:
    result = await db.execute(
        select(Professional).where(Professional.clinic_id == clinic_id).order_by(Professional.first_name)
    )
    return list(result.scalars().all())


async def create_professional(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: ProfessionalCreate
) -> Professional:
    professional = Professional(clinic_id=clinic_id, **payload.model_dump())
    db.add(professional)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="professional",
        entity_id=str(professional.id), after=payload.model_dump(mode="json"),
    )
    return professional


async def get_professional_or_404(db: AsyncSession, clinic_id: uuid.UUID, professional_id: uuid.UUID) -> Professional:
    result = await db.execute(
        select(Professional).where(Professional.id == professional_id, Professional.clinic_id == clinic_id)
    )
    professional = result.scalar_one_or_none()
    if professional is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesional no encontrado")
    return professional


async def update_professional(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, professional_id: uuid.UUID,
    payload: ProfessionalUpdate,
) -> Professional:
    professional = await get_professional_or_404(db, clinic_id, professional_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(professional, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="professional",
        entity_id=str(professional_id), after=data,
    )
    return professional
