import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.clinical_evolution.models import ClinicalEvolution
from app.modules.clinical_evolution.schemas import EvolutionCreate, EvolutionUpdate
from app.modules.patients.service import get_patient_or_404


async def list_evolutions(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[ClinicalEvolution]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(ClinicalEvolution)
        .where(ClinicalEvolution.clinic_id == clinic_id, ClinicalEvolution.patient_id == patient_id)
        .order_by(ClinicalEvolution.created_at.desc())
    )
    return list(result.scalars().all())


async def create_evolution(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: EvolutionCreate
) -> ClinicalEvolution:
    await get_patient_or_404(db, clinic_id, patient_id)
    entry = ClinicalEvolution(
        clinic_id=clinic_id,
        patient_id=patient_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    db.add(entry)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="clinical_evolution",
        entity_id=str(entry.id), after={"patient_id": str(patient_id), "procedure": entry.procedure},
    )
    return entry


async def get_or_404(db: AsyncSession, clinic_id: uuid.UUID, evolution_id: uuid.UUID) -> ClinicalEvolution:
    result = await db.execute(
        select(ClinicalEvolution).where(
            ClinicalEvolution.id == evolution_id, ClinicalEvolution.clinic_id == clinic_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evolución no encontrada")
    return entry


async def update_evolution(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, evolution_id: uuid.UUID,
    payload: EvolutionUpdate,
) -> ClinicalEvolution:
    """Corrections are allowed, but every change is recorded with its previous
    value — a clinical note is never silently rewritten."""
    entry = await get_or_404(db, clinic_id, evolution_id)
    data = payload.model_dump(exclude_unset=True)
    before = {field: getattr(entry, field) for field in data}
    for field, value in data.items():
        setattr(entry, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="clinical_evolution",
        entity_id=str(evolution_id), before=before, after=data,
    )
    return entry
