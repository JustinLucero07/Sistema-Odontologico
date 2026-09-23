import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.shared.voiding import apply_void
from app.modules.patients.service import get_patient_or_404
from app.modules.prescriptions.models import Prescription, PrescriptionItem
from app.modules.prescriptions.schemas import PrescriptionCreate


async def list_prescriptions(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Prescription]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.items))
        .where(Prescription.clinic_id == clinic_id, Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
    )
    return list(result.scalars().all())


async def create_prescription(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID,
    payload: PrescriptionCreate,
) -> Prescription:
    await get_patient_or_404(db, clinic_id, patient_id)
    from app.modules.professionals.service import get_professional_or_404

    professional = await get_professional_or_404(db, clinic_id, payload.professional_id)
    if not professional.is_active:
        raise HTTPException(status_code=400, detail="Ese profesional está desactivado y no puede prescribir")
    prescription = Prescription(
        clinic_id=clinic_id,
        patient_id=patient_id,
        professional_id=payload.professional_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        notes=payload.notes,
        items=[PrescriptionItem(clinic_id=clinic_id, **item.model_dump()) for item in payload.items],
    )
    db.add(prescription)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="prescription",
        entity_id=str(prescription.id),
        after={"patient_id": str(patient_id), "medications": [i.medication for i in payload.items]},
    )
    return prescription


async def void_prescription(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID,
    record_id: uuid.UUID, reason: str,
) -> Prescription:
    record = (
        await db.execute(
            select(Prescription)
        .options(selectinload(Prescription.items))
            .where(Prescription.id == record_id, Prescription.clinic_id == clinic_id, Prescription.patient_id == patient_id)
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La receta no existe")
    apply_void(record, actor_id, reason, "La receta")
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="void", entity_type="prescription",
        entity_id=str(record_id), after={"reason": record.void_reason},
    )
    return record
