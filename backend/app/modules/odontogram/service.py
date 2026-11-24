import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.odontogram.models import Odontogram, ToothCondition
from app.modules.odontogram.schemas import OdontogramCreate
from app.modules.patients.service import get_patient_or_404


async def get_latest(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> Odontogram | None:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Odontogram)
        .options(selectinload(Odontogram.conditions))
        .where(Odontogram.clinic_id == clinic_id, Odontogram.patient_id == patient_id)
        .order_by(Odontogram.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_version(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, odontogram_id: uuid.UUID
) -> Odontogram | None:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Odontogram)
        .options(selectinload(Odontogram.conditions))
        .where(
            Odontogram.id == odontogram_id,
            Odontogram.clinic_id == clinic_id,
            Odontogram.patient_id == patient_id,
        )
    )
    return result.scalar_one_or_none()


MAX_TIMELINE = 200


async def timeline(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[dict]:
    """Todas las versiones de la más antigua a la más nueva, con sus cambios."""
    from app.modules.users.models import User

    await get_patient_or_404(db, clinic_id, patient_id)
    versiones = list(
        (
            await db.execute(
                select(Odontogram)
                .options(selectinload(Odontogram.conditions))
                .where(Odontogram.clinic_id == clinic_id, Odontogram.patient_id == patient_id)
                .order_by(Odontogram.created_at.desc())
                .limit(MAX_TIMELINE)
            )
        ).scalars().all()
    )
    versiones.reverse()
    ids = {v.created_by_id for v in versiones if v.created_by_id}
    nombres = {}
    if ids:
        for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all():
            nombres[u.id] = f"{u.first_name} {u.last_name}".strip()

    def clave(c) -> tuple[str, str, str]:
        return (c.fdi_number, c.surface, c.condition)

    salida = []
    antes: set[tuple[str, str, str]] = set()
    for v in versiones:
        ahora = {clave(c) for c in v.conditions if c.condition != "sano"}
        como = lambda conjunto: [  # noqa: E731
            {"fdi_number": f, "surface": s, "condition": c} for f, s, c in sorted(conjunto)
        ]
        salida.append(
            {
                "id": v.id,
                "created_at": v.created_at,
                "type": v.type,
                "notes": v.notes,
                "author_name": nombres.get(v.created_by_id),
                "conditions": como(ahora),
                "added": como(ahora - antes),
                "removed": como(antes - ahora),
            }
        )
        antes = ahora
    return salida


async def list_versions(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Odontogram]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Odontogram)
        .where(Odontogram.clinic_id == clinic_id, Odontogram.patient_id == patient_id)
        .order_by(Odontogram.created_at.desc())
    )
    return list(result.scalars().all())


async def create_snapshot(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID,
    payload: OdontogramCreate,
) -> Odontogram:
    await get_patient_or_404(db, clinic_id, patient_id)
    previous = await get_latest(db, clinic_id, patient_id)

    odontogram = Odontogram(
        clinic_id=clinic_id,
        patient_id=patient_id,
        professional_id=payload.professional_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        previous_odontogram_id=previous.id if previous else None,
        notes=payload.notes,
        conditions=[
            ToothCondition(
                clinic_id=clinic_id,
                fdi_number=c.fdi_number,
                surface=c.surface,
                condition=c.condition,
                notes=c.notes,
            )
            for c in payload.conditions
        ],
    )
    db.add(odontogram)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="odontogram",
        entity_id=str(odontogram.id), after={"patient_id": str(patient_id), "conditions": len(payload.conditions)},
    )
    return odontogram
