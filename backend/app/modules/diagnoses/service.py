import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.diagnoses.models import Diagnosis
from app.modules.diagnoses.schemas import DiagnosisCreate
from app.modules.patients.service import get_patient_or_404


async def list_diagnoses(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Diagnosis]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Diagnosis)
        .where(Diagnosis.clinic_id == clinic_id, Diagnosis.patient_id == patient_id)
        .order_by(Diagnosis.created_at.desc())
    )
    return list(result.scalars().all())


async def create_diagnosis(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: DiagnosisCreate
) -> Diagnosis:
    await get_patient_or_404(db, clinic_id, patient_id)
    diagnosis = Diagnosis(
        clinic_id=clinic_id,
        patient_id=patient_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    db.add(diagnosis)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="diagnosis",
        entity_id=str(diagnosis.id), after={"patient_id": str(patient_id), "description": diagnosis.description},
    )
    return diagnosis
