import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.laboratory.constants import STATUS_ORDER, TERMINAL_STATUSES
from app.modules.laboratory.models import LabOrder, LabOrderEvent, Laboratory
from app.modules.laboratory.schemas import (
    LabOrderCreate,
    LabOrderOut,
    LabOrderStatusUpdate,
    LabOrderUpdate,
    LaboratoryIn,
)
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404


# ---- Laboratories -------------------------------------------------------


async def list_laboratories(db: AsyncSession, clinic_id: uuid.UUID) -> list[Laboratory]:
    result = await db.execute(
        select(Laboratory).where(Laboratory.clinic_id == clinic_id).order_by(Laboratory.name)
    )
    return list(result.scalars().all())


async def create_laboratory(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: LaboratoryIn
) -> Laboratory:
    lab = Laboratory(clinic_id=clinic_id, **payload.model_dump())
    db.add(lab)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="laboratory",
        entity_id=str(lab.id), after={"name": lab.name},
    )
    return lab


async def update_laboratory(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, laboratory_id: uuid.UUID, payload: LaboratoryIn
) -> Laboratory:
    lab = await _get_laboratory_or_404(db, clinic_id, laboratory_id)
    for field, value in payload.model_dump().items():
        setattr(lab, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="laboratory",
        entity_id=str(laboratory_id), after=payload.model_dump(mode="json"),
    )
    return lab


async def _get_laboratory_or_404(db: AsyncSession, clinic_id: uuid.UUID, laboratory_id: uuid.UUID) -> Laboratory:
    lab = (
        await db.execute(select(Laboratory).where(Laboratory.id == laboratory_id, Laboratory.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laboratorio no encontrado")
    return lab


# ---- Orders -------------------------------------------------------------


def to_order_out(order: LabOrder, patient_name: str | None, today: date | None = None) -> LabOrderOut:
    today = today or date.today()
    # Only a case still out at the lab can be late; one already installed or
    # cancelled is finished, however long it took.
    overdue = None
    if order.due_on and order.status not in TERMINAL_STATUSES and order.received_on is None:
        delta = (today - order.due_on).days
        overdue = delta if delta > 0 else None

    return LabOrderOut(
        id=order.id,
        patient_id=order.patient_id,
        patient_name=patient_name,
        laboratory_id=order.laboratory_id,
        laboratory_name=order.laboratory.name if order.laboratory else None,
        professional_id=order.professional_id,
        treatment_plan_item_id=order.treatment_plan_item_id,
        work_type=order.work_type,
        description=order.description,
        fdi_numbers=order.fdi_numbers,
        shade=order.shade,
        material=order.material,
        status=order.status,
        sent_on=order.sent_on,
        due_on=order.due_on,
        received_on=order.received_on,
        cost=order.cost,
        notes=order.notes,
        created_at=order.created_at,
        events=order.events,
        days_overdue=overdue,
    )


def _order_query():
    return select(LabOrder, Patient.first_name, Patient.last_name).join(
        Patient, LabOrder.patient_id == Patient.id
    ).options(selectinload(LabOrder.events), selectinload(LabOrder.laboratory))


async def get_order_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, order_id: uuid.UUID
) -> tuple[LabOrder, str]:
    result = await db.execute(
        _order_query().where(LabOrder.id == order_id, LabOrder.clinic_id == clinic_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajo no encontrado")
    order, first, last = row
    return order, f"{first} {last}"


async def list_orders(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    patient_id: uuid.UUID | None = None,
    open_only: bool = False,
) -> list[LabOrderOut]:
    query = _order_query().where(LabOrder.clinic_id == clinic_id)
    if patient_id is not None:
        query = query.where(LabOrder.patient_id == patient_id)
    if open_only:
        query = query.where(LabOrder.status.not_in(tuple(TERMINAL_STATUSES)))
    result = await db.execute(query.order_by(LabOrder.created_at.desc()))
    return [to_order_out(o, f"{first} {last}") for o, first, last in result.all()]


async def create_order(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: LabOrderCreate
) -> LabOrderOut:
    await get_patient_or_404(db, clinic_id, payload.patient_id)

    lab = (
        await db.execute(
            select(Laboratory).where(
                Laboratory.id == payload.laboratory_id, Laboratory.clinic_id == clinic_id
            )
        )
    ).scalar_one_or_none()
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laboratorio no encontrado")

    # A due date nobody set is proposed from the lab's own turnaround rather
    # than left blank, so the case can still show up as late.
    due_on = payload.due_on
    if due_on is None and lab.default_turnaround_days:
        due_on = date.today() + timedelta(days=lab.default_turnaround_days)

    order = LabOrder(
        clinic_id=clinic_id,
        patient_id=payload.patient_id,
        laboratory_id=payload.laboratory_id,
        professional_id=payload.professional_id,
        treatment_plan_item_id=payload.treatment_plan_item_id,
        work_type=payload.work_type,
        description=payload.description,
        fdi_numbers=payload.fdi_numbers or None,
        shade=payload.shade,
        material=payload.material,
        status="borrador",
        due_on=due_on,
        cost=payload.cost,
        notes=payload.notes,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
    )
    order.events.append(
        LabOrderEvent(
            clinic_id=clinic_id,
            status="borrador",
            note="Trabajo creado",
            created_by_id=actor_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.add(order)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="lab_order",
        entity_id=str(order.id),
        after={"patient_id": str(payload.patient_id), "work_type": payload.work_type},
    )
    created, patient_name = await get_order_or_404(db, clinic_id, order.id)
    return to_order_out(created, patient_name)


async def update_status(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    order_id: uuid.UUID,
    payload: LabOrderStatusUpdate,
) -> LabOrderOut:
    order, patient_name = await get_order_or_404(db, clinic_id, order_id)

    if order.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El trabajo ya está «{order.status}» y no admite más cambios",
        )

    # The chain only runs forward. A case that comes back wrong is recorded as
    # "rechazado" — an event in its own right — rather than quietly rewound,
    # because how many times a crown was remade is part of the case.
    if payload.status in STATUS_ORDER and order.status in STATUS_ORDER:
        if STATUS_ORDER.index(payload.status) < STATUS_ORDER.index(order.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"No se puede retroceder de «{order.status}» a «{payload.status}». "
                    "Use «rechazado» si el trabajo volvió del laboratorio."
                ),
            )

    before = order.status
    order.status = payload.status
    now = datetime.now(timezone.utc)
    if payload.status == "enviado" and order.sent_on is None:
        order.sent_on = date.today()
    if payload.status == "recibido" and order.received_on is None:
        order.received_on = date.today()
    if payload.status == "rechazado":
        # It went back out, so it is no longer in the clinic.
        order.received_on = None

    order.events.append(
        LabOrderEvent(
            clinic_id=clinic_id,
            status=payload.status,
            note=payload.note,
            created_by_id=actor_id,
            created_at=now,
        )
    )
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="lab_order",
        entity_id=str(order_id), before={"status": before}, after={"status": payload.status},
    )
    return to_order_out(order, patient_name)


async def update_order(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    order_id: uuid.UUID,
    payload: LabOrderUpdate,
) -> LabOrderOut:
    order, patient_name = await get_order_or_404(db, clinic_id, order_id)
    if order.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El trabajo ya está «{order.status}»: sus datos quedan como se cerraron",
        )
    if payload.laboratory_id != order.laboratory_id:
        await _get_laboratory_or_404(db, clinic_id, payload.laboratory_id)

    before = {"description": order.description, "due_on": str(order.due_on), "cost": str(order.cost)}
    for field, value in payload.model_dump().items():
        setattr(order, field, value)
    await db.flush()
    # La relación cargada sigue apuntando al laboratorio anterior hasta recargarla.
    await db.refresh(order, attribute_names=["laboratory"])
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="lab_order",
        entity_id=str(order_id), before=before, after=payload.model_dump(mode="json"),
    )
    updated, patient_name = await get_order_or_404(db, clinic_id, order_id)
    return to_order_out(updated, patient_name)
