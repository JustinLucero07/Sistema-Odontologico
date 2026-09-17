import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.medical_history.models import MedicalHistory
from app.modules.medical_history.schemas import MedicalHistoryCreate
from app.modules.patients.service import get_patient_or_404


async def get_latest(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> MedicalHistory | None:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(MedicalHistory)
        .where(MedicalHistory.clinic_id == clinic_id, MedicalHistory.patient_id == patient_id)
        .order_by(MedicalHistory.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_versions(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[MedicalHistory]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(MedicalHistory)
        .where(MedicalHistory.clinic_id == clinic_id, MedicalHistory.patient_id == patient_id)
        .order_by(MedicalHistory.created_at.desc())
    )
    return list(result.scalars().all())


async def create_version(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID,
    payload: MedicalHistoryCreate,
) -> MedicalHistory:
    await get_patient_or_404(db, clinic_id, patient_id)

    entry = MedicalHistory(
        clinic_id=clinic_id,
        patient_id=patient_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    db.add(entry)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="medical_history",
        entity_id=str(entry.id), after={"patient_id": str(patient_id)},
    )
    return entry
