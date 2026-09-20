import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.patients.service import get_patient_or_404
from app.modules.periodontogram.models import (
    Periodontogram,
    PeriodontalMeasurement,
    PeriodontalTooth,
)
from app.modules.periodontogram.schemas import PeriodontogramCreate

_LOADERS = (
    selectinload(Periodontogram.teeth),
    selectinload(Periodontogram.measurements),
)


async def get_latest(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Periodontogram | None:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Periodontogram)
        .options(*_LOADERS)
        .where(Periodontogram.clinic_id == clinic_id, Periodontogram.patient_id == patient_id)
        .order_by(Periodontogram.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_version(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, periodontogram_id: uuid.UUID
) -> Periodontogram | None:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Periodontogram)
        .options(*_LOADERS)
        .where(
            Periodontogram.id == periodontogram_id,
            Periodontogram.clinic_id == clinic_id,
            Periodontogram.patient_id == patient_id,
        )
    )
    return result.scalar_one_or_none()


async def list_versions(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Periodontogram]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Periodontogram)
        .where(Periodontogram.clinic_id == clinic_id, Periodontogram.patient_id == patient_id)
        .order_by(Periodontogram.created_at.desc())
    )
    return list(result.scalars().all())


async def create_snapshot(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: PeriodontogramCreate,
) -> Periodontogram:
    await get_patient_or_404(db, clinic_id, patient_id)

    # One row per tooth/site. A duplicate means the client sent the same probe
    # reading twice, which would silently skew every index computed from it.
    seen: set[tuple[str, str]] = set()
    for m in payload.measurements:
        key = (m.fdi_number, m.site)
        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Medición duplicada para la pieza {m.fdi_number} en {m.site}",
            )
        seen.add(key)

    previous = await get_latest(db, clinic_id, patient_id)

    periodontogram = Periodontogram(
        clinic_id=clinic_id,
        patient_id=patient_id,
        professional_id=payload.professional_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        previous_periodontogram_id=previous.id if previous else None,
        notes=payload.notes,
        teeth=[
            PeriodontalTooth(
                clinic_id=clinic_id,
                fdi_number=t.fdi_number,
                absent=t.absent,
                implant=t.implant,
                mobility=t.mobility,
                furcation=t.furcation,
                notes=t.notes,
            )
            for t in payload.teeth
        ],
        measurements=[
            PeriodontalMeasurement(
                clinic_id=clinic_id,
                fdi_number=m.fdi_number,
                site=m.site,
                probing_depth=m.probing_depth,
                recession=m.recession,
                bleeding=m.bleeding,
                suppuration=m.suppuration,
                plaque=m.plaque,
            )
            for m in payload.measurements
        ],
    )
    db.add(periodontogram)
    await db.flush()
    await record_audit(
        db,
        clinic_id=clinic_id,
        user_id=actor_id,
        action="create",
        entity_type="periodontogram",
        entity_id=str(periodontogram.id),
        after={
            "patient_id": str(patient_id),
            "teeth": len(payload.teeth),
            "measurements": len(payload.measurements),
        },
    )
    return periodontogram
