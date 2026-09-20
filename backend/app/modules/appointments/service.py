import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.appointments.constants import (
    DEFAULT_REMINDER_OFFSETS_MINUTES,
    SLOT_FREEING_STATUSES,
)
from app.modules.appointments.models import Appointment, AppointmentReminder
from app.modules.appointments.schemas import AppointmentCreate, AppointmentUpdate
from app.modules.patients.service import get_patient_or_404
from app.modules.professionals.service import get_professional_or_404


def _appointment_query():
    return select(Appointment).options(
        selectinload(Appointment.reminders),
        selectinload(Appointment.patient),
        selectinload(Appointment.professional),
        selectinload(Appointment.treatment),
    )


async def list_appointments(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
    professional_id: uuid.UUID | None = None,
    include_cancelled: bool = True,
) -> list[Appointment]:
    query = _appointment_query().where(
        Appointment.clinic_id == clinic_id,
        Appointment.starts_at < date_to,
        Appointment.ends_at > date_from,
    )
    if professional_id is not None:
        query = query.where(Appointment.professional_id == professional_id)
    if not include_cancelled:
        query = query.where(Appointment.status.notin_(list(SLOT_FREEING_STATUSES)))

    result = await db.execute(query.order_by(Appointment.starts_at))
    return list(result.scalars().all())


async def list_patient_appointments(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Appointment]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        _appointment_query()
        .where(Appointment.clinic_id == clinic_id, Appointment.patient_id == patient_id)
        .order_by(Appointment.starts_at.desc())
    )
    return list(result.scalars().all())


async def get_appointment_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> Appointment:
    result = await db.execute(
        _appointment_query().where(Appointment.id == appointment_id, Appointment.clinic_id == clinic_id)
    )
    appointment = result.scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return appointment


async def _assert_slot_free(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    professional_id: uuid.UUID,
    operatory_id: uuid.UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Friendly pre-check so the user gets a clear message instead of a raw
    constraint violation. The database constraint is still the real guarantee
    against two bookings racing each other."""
    conflicts = or_(Appointment.professional_id == professional_id)
    if operatory_id is not None:
        conflicts = or_(Appointment.professional_id == professional_id, Appointment.operatory_id == operatory_id)

    query = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.status.notin_(list(SLOT_FREEING_STATUSES)),
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
        conflicts,
    )
    if exclude_id is not None:
        query = query.where(Appointment.id != exclude_id)

    existing = (await db.execute(query.limit(1))).scalar_one_or_none()
    if existing is not None:
        clash = "el profesional" if existing.professional_id == professional_id else "el consultorio"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ese horario ya está ocupado para {clash}",
        )


def _build_reminders(
    clinic_id: uuid.UUID, starts_at: datetime, channels: list[str]
) -> list[AppointmentReminder]:
    now = datetime.now(timezone.utc)
    reminders: list[AppointmentReminder] = []
    for channel in channels:
        for offset in DEFAULT_REMINDER_OFFSETS_MINUTES:
            scheduled_for = starts_at - timedelta(minutes=offset)
            # A reminder whose moment already passed would never be useful.
            if scheduled_for <= now:
                continue
            reminders.append(
                AppointmentReminder(
                    clinic_id=clinic_id,
                    channel=channel,
                    offset_minutes=offset,
                    scheduled_for=scheduled_for,
                    status="pendiente",
                    created_at=now,
                )
            )
    return reminders


async def create_appointment(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: AppointmentCreate
) -> Appointment:
    await get_patient_or_404(db, clinic_id, payload.patient_id)
    await get_professional_or_404(db, clinic_id, payload.professional_id)
    await _assert_slot_free(
        db, clinic_id, payload.professional_id, payload.operatory_id, payload.starts_at, payload.ends_at
    )

    appointment = Appointment(
        clinic_id=clinic_id,
        created_by_id=actor_id,
        reminders=_build_reminders(clinic_id, payload.starts_at, payload.reminder_channels),
        **payload.model_dump(exclude={"reminder_channels"}),
    )
    db.add(appointment)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese horario acaba de ser ocupado por otra reserva",
        ) from exc

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="appointment",
        entity_id=str(appointment.id),
        after={"patient_id": str(payload.patient_id), "starts_at": payload.starts_at},
    )
    return await get_appointment_or_404(db, clinic_id, appointment.id)


async def update_appointment(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
) -> Appointment:
    appointment = await get_appointment_or_404(db, clinic_id, appointment_id)
    data = payload.model_dump(exclude_unset=True)

    starts_at = data.get("starts_at", appointment.starts_at)
    ends_at = data.get("ends_at", appointment.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La hora de fin debe ser posterior a la de inicio",
        )

    professional_id = data.get("professional_id", appointment.professional_id)
    operatory_id = data.get("operatory_id", appointment.operatory_id)
    if appointment.status not in SLOT_FREEING_STATUSES:
        await _assert_slot_free(
            db, clinic_id, professional_id, operatory_id, starts_at, ends_at, exclude_id=appointment.id
        )

    before = {"starts_at": appointment.starts_at, "ends_at": appointment.ends_at}
    for field, value in data.items():
        setattr(appointment, field, value)

    # Rescheduling invalidates any reminder still waiting to go out.
    if "starts_at" in data:
        for reminder in appointment.reminders:
            if reminder.status == "pendiente":
                reminder.scheduled_for = appointment.starts_at - timedelta(minutes=reminder.offset_minutes)

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="appointment",
        entity_id=str(appointment_id), before=before, after=data,
    )
    return await get_appointment_or_404(db, clinic_id, appointment_id)


async def update_status(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, appointment_id: uuid.UUID,
    new_status: str, cancellation_reason: str | None,
) -> Appointment:
    appointment = await get_appointment_or_404(db, clinic_id, appointment_id)
    before_status = appointment.status
    appointment.status = new_status
    if new_status in SLOT_FREEING_STATUSES:
        appointment.cancellation_reason = cancellation_reason
        # No point reminding a patient about an appointment that is off.
        for reminder in appointment.reminders:
            if reminder.status == "pendiente":
                reminder.status = "cancelado"

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="appointment",
        entity_id=str(appointment_id), before={"status": before_status}, after={"status": new_status},
    )
    return await get_appointment_or_404(db, clinic_id, appointment_id)


async def list_due_reminders(db: AsyncSession, clinic_id: uuid.UUID) -> list[AppointmentReminder]:
    """Reminders whose moment has arrived and that nothing has sent yet. The
    messaging integrations of a later phase consume this; sending is not this
    module's job."""
    result = await db.execute(
        select(AppointmentReminder)
        .where(
            AppointmentReminder.clinic_id == clinic_id,
            AppointmentReminder.status == "pendiente",
            AppointmentReminder.scheduled_for <= datetime.now(timezone.utc),
        )
        .order_by(AppointmentReminder.scheduled_for)
    )
    return list(result.scalars().all())
