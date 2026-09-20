import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.appointments import service
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentReminderOut,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])
patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/appointments", tags=["appointments"])


def _out(appointment) -> AppointmentOut:
    return AppointmentOut.from_appointment(
        appointment, appointment.patient, appointment.professional, appointment.treatment
    )


@router.get("", response_model=list[AppointmentOut])
async def get_appointments(
    date_from: datetime = Query(alias="from"),
    date_to: datetime = Query(alias="to"),
    professional_id: uuid.UUID | None = Query(default=None),
    include_cancelled: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    appointments = await service.list_appointments(
        db, current_user.clinic_id, date_from, date_to, professional_id, include_cancelled
    )
    return [_out(a) for a in appointments]


@router.post("", response_model=AppointmentOut, status_code=201)
async def post_appointment(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:write")),
):
    appointment = await service.create_appointment(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return _out(appointment)


@router.get("/reminders/due", response_model=list[AppointmentReminderOut])
async def get_due_reminders(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return await service.list_due_reminders(db, current_user.clinic_id)


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return _out(await service.get_appointment_or_404(db, current_user.clinic_id, appointment_id))


@router.put("/{appointment_id}", response_model=AppointmentOut)
async def put_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:write")),
):
    appointment = await service.update_appointment(
        db, current_user.clinic_id, current_user.id, appointment_id, payload
    )
    await db.commit()
    return _out(appointment)


@router.put("/{appointment_id}/status", response_model=AppointmentOut)
async def put_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:write")),
):
    appointment = await service.update_status(
        db, current_user.clinic_id, current_user.id, appointment_id, payload.status, payload.cancellation_reason
    )
    await db.commit()
    return _out(appointment)


@patient_router.get("", response_model=list[AppointmentOut])
async def get_patient_appointments(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    appointments = await service.list_patient_appointments(db, current_user.clinic_id, patient_id)
    return [_out(a) for a in appointments]
