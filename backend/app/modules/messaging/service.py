import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.appointments.models import Appointment, AppointmentReminder
from app.modules.clinics.models import Clinic
from app.modules.messaging.models import MessageTemplate, OutboundMessage
from app.modules.messaging.schemas import (
    DispatchResult,
    MessageCreate,
    ProviderStatus,
    TemplateIn,
)
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.shared.messaging import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_SENT,
    STATUS_SIMULATED,
    get_messaging,
)
from app.modules.privacy.service import communications_revoked

# Templates a clinic gets on day one. They are seeded per clinic on first use
# so a practice can edit its own wording without touching anyone else's.
DEFAULT_TEMPLATES = [
    (
        "recordatorio_cita",
        "Recordatorio de cita",
        "Hola {paciente}, le recordamos su cita en {clinica} el {fecha} a las {hora}. "
        "Si no puede asistir, por favor avísenos.",
    ),
    (
        "confirmacion_cita",
        "Confirmación de cita",
        "Hola {paciente}, su cita en {clinica} quedó agendada para el {fecha} a las {hora}. "
        "¡Le esperamos!",
    ),
    (
        "recitacion",
        "Invitación a control",
        "Hola {paciente}, hace tiempo que no le vemos por {clinica}. "
        "Si desea agendar un control, responda a este mensaje.",
    ),
]


def provider_status() -> ProviderStatus:
    provider = get_messaging()
    return ProviderStatus(
        provider=provider.name,
        is_live=provider.is_live,
        message=(
            "Los mensajes se envían realmente por WhatsApp."
            if provider.is_live
            else "No hay proveedor configurado: los mensajes se registran como «simulado» "
            "y no salen del servidor."
        ),
    )


# ---- Templates ----------------------------------------------------------


async def list_templates(db: AsyncSession, clinic_id: uuid.UUID) -> list[MessageTemplate]:
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.clinic_id == clinic_id).order_by(MessageTemplate.name)
    )
    templates = list(result.scalars().all())
    if templates:
        return templates

    # First visit: give the clinic something to edit rather than an empty page.
    for code, name, body in DEFAULT_TEMPLATES:
        db.add(
            MessageTemplate(
                clinic_id=clinic_id, code=code, name=name, channel="whatsapp", body=body
            )
        )
    await db.flush()
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.clinic_id == clinic_id).order_by(MessageTemplate.name)
    )
    return list(result.scalars().all())


async def upsert_template(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: TemplateIn
) -> MessageTemplate:
    existing = (
        await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.clinic_id == clinic_id, MessageTemplate.code == payload.code
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = MessageTemplate(clinic_id=clinic_id, code=payload.code)
        db.add(existing)
    for field, value in payload.model_dump(exclude={"code"}).items():
        setattr(existing, field, value)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="message_template",
        entity_id=str(existing.id), after={"code": payload.code},
    )
    return existing


def render(body: str, values: dict[str, str]) -> str:
    """Substitutes {placeholders}. An unknown one is left visible rather than
    blanked, so a broken template is obvious in the preview instead of going
    out as 'Hola , le recordamos...'."""
    out = body
    for key, value in values.items():
        out = out.replace("{" + key + "}", value)
    return out


# ---- Sending ------------------------------------------------------------


async def _placeholders(
    db: AsyncSession, clinic_id: uuid.UUID, patient: Patient, appointment: Appointment | None = None
) -> dict[str, str]:
    """Every placeholder a template can use, filled from real data.

    Anything left unfilled stays visible as `{nombre}` — a template with a typo
    should look broken in the preview, not go out reading "Hola , le
    recordamos". That only works if the ones we DO know are all here."""
    clinic = (
        await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    ).scalar_one_or_none()
    values = {
        "paciente": patient.first_name,
        "nombre_completo": f"{patient.first_name} {patient.last_name}",
        "clinica": clinic.name if clinic else "la clínica",
    }
    if appointment is not None:
        local = appointment.starts_at.astimezone(timezone.utc)
        values["fecha"] = local.strftime("%d/%m/%Y")
        values["hora"] = local.strftime("%H:%M")
    return values


def _destination(patient: Patient, channel: str) -> str:
    address = (
        (patient.whatsapp or patient.phone)
        if channel in ("whatsapp", "sms")
        else patient.email
    )
    if not address:
        field = "WhatsApp o teléfono" if channel in ("whatsapp", "sms") else "correo electrónico"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El paciente no tiene {field} registrado",
        )
    return address


async def send_message(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: MessageCreate
) -> OutboundMessage:
    patient = await get_patient_or_404(db, clinic_id, payload.patient_id)
    if await communications_revoked(db, clinic_id, patient.id):
        raise HTTPException(
            status_code=409,
            detail="El paciente retiró su autorización para recibir mensajes. Contáctelo por otra vía.",
        )

    body = payload.body
    if not body and payload.template_code:
        template = (
            await db.execute(
                select(MessageTemplate).where(
                    MessageTemplate.clinic_id == clinic_id,
                    MessageTemplate.code == payload.template_code,
                )
            )
        ).scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        body = render(template.body, await _placeholders(db, clinic_id, patient))
    if not body or not body.strip():
        raise HTTPException(status_code=400, detail="El mensaje está vacío")

    to_address = _destination(patient, payload.channel)
    result = await get_messaging().send(to_address, body)

    message = OutboundMessage(
        clinic_id=clinic_id,
        patient_id=patient.id,
        appointment_id=payload.appointment_id,
        channel=payload.channel,
        to_address=to_address,
        body=body,
        status=result.status,
        provider=result.provider,
        provider_message_id=result.provider_message_id,
        error=result.error,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        # Only a real delivery gets a send timestamp. A simulated message has
        # no moment at which it reached anyone.
        sent_at=datetime.now(timezone.utc) if result.status == STATUS_SENT else None,
    )
    db.add(message)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="send", entity_type="message",
        entity_id=str(message.id),
        after={"patient_id": str(patient.id), "channel": payload.channel, "status": result.status},
    )
    return message


async def list_messages(
    db: AsyncSession, clinic_id: uuid.UUID, *, patient_id: uuid.UUID | None = None, limit: int = 100
) -> list[OutboundMessage]:
    query = select(OutboundMessage).where(OutboundMessage.clinic_id == clinic_id)
    if patient_id is not None:
        query = query.where(OutboundMessage.patient_id == patient_id)
    result = await db.execute(query.order_by(OutboundMessage.created_at.desc()).limit(limit))
    return list(result.scalars().all())


# ---- Reminder dispatch --------------------------------------------------


async def dispatch_due_reminders(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID | None = None
) -> DispatchResult:
    """Turns reminders whose moment has arrived into real messages.

    Phase 5 recorded WHAT should go out and WHEN but deliberately sent nothing.
    This is the other half. It is idempotent by status: a reminder already
    resolved is never picked up twice, so running it repeatedly is safe."""
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(AppointmentReminder)
            .options(selectinload(AppointmentReminder.appointment).selectinload(Appointment.patient))
            .where(
                AppointmentReminder.clinic_id == clinic_id,
                AppointmentReminder.status == "pendiente",
                AppointmentReminder.scheduled_for <= now,
            )
        )
    ).scalars().all()

    result = DispatchResult(due=len(rows), sent=0, simulated=0, failed=0, skipped=0)
    provider = get_messaging()

    for reminder in rows:
        appointment = reminder.appointment
        # A cancelled or already-attended appointment must not send a reminder;
        # the patient is not coming, or has already been.
        if appointment is None or appointment.status in ("cancelada", "atendida", "no_asistio"):
            reminder.status = STATUS_CANCELLED
            result.skipped += 1
            continue

        patient = appointment.patient
        if await communications_revoked(db, clinic_id, patient.id):
            reminder.status = STATUS_CANCELLED
            reminder.error = "El paciente retiró su autorización para recibir mensajes"
            result.skipped += 1
            continue
        try:
            to_address = _destination(patient, reminder.channel)
        except HTTPException as exc:
            reminder.status = STATUS_FAILED
            reminder.error = exc.detail
            result.failed += 1
            continue

        body = render(
            DEFAULT_TEMPLATES[0][2],
            await _placeholders(db, clinic_id, patient, appointment),
        )

        delivery = await provider.send(to_address, body)
        db.add(
            OutboundMessage(
                clinic_id=clinic_id,
                patient_id=patient.id,
                appointment_id=appointment.id,
                reminder_id=reminder.id,
                channel=reminder.channel,
                to_address=to_address,
                body=body,
                status=delivery.status,
                provider=delivery.provider,
                provider_message_id=delivery.provider_message_id,
                error=delivery.error,
                created_by_id=actor_id,
                created_at=now,
                sent_at=now if delivery.status == STATUS_SENT else None,
            )
        )
        reminder.status = delivery.status
        reminder.error = delivery.error
        reminder.sent_at = now if delivery.status == STATUS_SENT else None

        if delivery.status == STATUS_SENT:
            result.sent += 1
        elif delivery.status == STATUS_SIMULATED:
            result.simulated += 1
        else:
            result.failed += 1

    await db.flush()
    return result
