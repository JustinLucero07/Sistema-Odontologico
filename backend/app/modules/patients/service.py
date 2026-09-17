import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientCreate, PatientUpdate


async def list_patients(db: AsyncSession, clinic_id: uuid.UUID, search: str | None = None) -> list[Patient]:
    query = select(Patient).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                Patient.national_id.ilike(term),
                Patient.phone.ilike(term),
                Patient.email.ilike(term),
            )
        )
    query = query.order_by(Patient.first_name, Patient.last_name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_patient_or_404(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return patient


async def create_patient(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: PatientCreate
) -> Patient:
    patient = Patient(clinic_id=clinic_id, **payload.model_dump())
    db.add(patient)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="patient",
        entity_id=str(patient.id), after={"first_name": patient.first_name, "last_name": patient.last_name},
    )
    return patient


async def update_patient(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: PatientUpdate
) -> Patient:
    patient = await get_patient_or_404(db, clinic_id, patient_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(patient, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="patient",
        entity_id=str(patient_id), after=data,
    )
    return patient


async def deactivate_patient(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    patient = await get_patient_or_404(db, clinic_id, patient_id)
    patient.deleted_at = datetime.now(timezone.utc)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="patient",
        entity_id=str(patient_id),
    )
