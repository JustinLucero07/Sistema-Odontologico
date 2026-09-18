import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.treatments.models import Treatment
from app.modules.treatments.schemas import TreatmentCreate, TreatmentUpdate


async def list_treatments(db: AsyncSession, clinic_id: uuid.UUID, include_inactive: bool = False) -> list[Treatment]:
    query = select(Treatment).where(Treatment.clinic_id == clinic_id)
    if not include_inactive:
        query = query.where(Treatment.is_active.is_(True))
    query = query.order_by(Treatment.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_treatment_or_404(db: AsyncSession, clinic_id: uuid.UUID, treatment_id: uuid.UUID) -> Treatment:
    result = await db.execute(select(Treatment).where(Treatment.id == treatment_id, Treatment.clinic_id == clinic_id))
    treatment = result.scalar_one_or_none()
    if treatment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tratamiento no encontrado")
    return treatment


async def create_treatment(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: TreatmentCreate
) -> Treatment:
    treatment = Treatment(clinic_id=clinic_id, **payload.model_dump())
    db.add(treatment)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="treatment",
        entity_id=str(treatment.id), after={"name": treatment.name},
    )
    return treatment


async def update_treatment(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, treatment_id: uuid.UUID, payload: TreatmentUpdate
) -> Treatment:
    treatment = await get_treatment_or_404(db, clinic_id, treatment_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(treatment, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="treatment",
        entity_id=str(treatment_id), after=data,
    )
    return treatment
