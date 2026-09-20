import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.core.config import get_settings
from app.modules.appointments.models import Appointment
from app.modules.clinics.models import Clinic
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.modules.payments.constants import money
from app.modules.payments.models import Charge, Payment
from app.modules.portal.models import PortalAccess
from app.modules.portal.schemas import PortalAppointment, PortalCharge, PortalView

ZERO = Decimal("0.00")

APPOINTMENT_LABELS = {
    "programada": "Programada",
    "confirmada": "Confirmada",
    "en_espera": "En espera",
    "en_atencion": "En atención",
    "atendida": "Atendida",
    "cancelada": "Cancelada",
    "no_asistio": "No asistió",
}


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_link(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID
) -> tuple[PortalAccess, str]:
    """Issues a link. Returns the access row and the RAW token, which the
    caller must hand over immediately — only the hash is kept, so it can never
    be shown again."""
    await get_patient_or_404(db, clinic_id, patient_id)
    settings = get_settings()

    raw = secrets.token_urlsafe(48)
    access = PortalAccess(
        clinic_id=clinic_id,
        patient_id=patient_id,
        token_hash=_hash(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.PORTAL_LINK_DAYS),
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(access)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="portal_access",
        entity_id=str(access.id), after={"patient_id": str(patient_id)},
    )
    return access, raw


async def list_links(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PortalAccess]:
    result = await db.execute(
        select(PortalAccess)
        .where(PortalAccess.clinic_id == clinic_id, PortalAccess.patient_id == patient_id)
        .order_by(PortalAccess.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, access_id: uuid.UUID, reason: str | None
) -> PortalAccess:
    access = (
        await db.execute(
            select(PortalAccess).where(
                PortalAccess.id == access_id, PortalAccess.clinic_id == clinic_id
            )
        )
    ).scalar_one_or_none()
    if access is None:
        raise HTTPException(status_code=404, detail="Enlace no encontrado")
    if access.revoked_at is not None:
        raise HTTPException(status_code=409, detail="El enlace ya está revocado")

    access.revoked_at = datetime.now(timezone.utc)
    access.revoked_reason = reason
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="revoke", entity_type="portal_access",
        entity_id=str(access_id), after={"reason": reason},
    )
    return access


async def resolve(db: AsyncSession, raw_token: str) -> PortalAccess:
    """Looks a token up by its hash and refuses anything not currently valid.

    Expired and revoked give the SAME answer as a token that never existed:
    telling an anonymous caller which of the three it is would let them map
    valid links by trying."""
    result = await db.execute(
        select(PortalAccess).where(PortalAccess.token_hash == _hash(raw_token))
    )
    access = result.scalar_one_or_none()
    if access is None or not access.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El enlace no es válido o ha caducado. Solicite uno nuevo a su clínica.",
        )
    return access


async def build_view(db: AsyncSession, access: PortalAccess) -> PortalView:
    """What the patient sees. Narrow on purpose: appointments and money, never
    clinical notes, diagnoses or documents — a link can end up in the wrong
    inbox, and the blast radius has to stay small."""
    patient = (
        await db.execute(select(Patient).where(Patient.id == access.patient_id))
    ).scalar_one()
    clinic = (
        await db.execute(select(Clinic).where(Clinic.id == access.clinic_id))
    ).scalar_one()

    now = datetime.now(timezone.utc)
    appointments = (
        await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.professional), selectinload(Appointment.treatment)
            )
            .where(
                Appointment.clinic_id == access.clinic_id,
                Appointment.patient_id == access.patient_id,
            )
            .order_by(Appointment.starts_at.desc())
            .limit(40)
        )
    ).scalars().all()

    def to_row(a: Appointment) -> PortalAppointment:
        professional = a.professional
        return PortalAppointment(
            starts_at=a.starts_at,
            professional_name=(
                f"{professional.first_name} {professional.last_name}" if professional else None
            ),
            treatment_name=a.treatment.name if a.treatment else None,
            status=APPOINTMENT_LABELS.get(a.status, a.status),
        )

    upcoming = [to_row(a) for a in reversed(appointments) if a.starts_at >= now and a.status != "cancelada"]
    past = [to_row(a) for a in appointments if a.starts_at < now][:10]

    charges = (
        await db.execute(
            select(Charge).where(
                Charge.clinic_id == access.clinic_id,
                Charge.patient_id == access.patient_id,
                Charge.voided_at.is_(None),
            )
        )
    ).scalars().all()
    payments = (
        await db.execute(
            select(Payment.charge_id, Payment.amount).where(
                Payment.clinic_id == access.clinic_id,
                Payment.patient_id == access.patient_id,
                Payment.voided_at.is_(None),
            )
        )
    ).all()

    paid_by_charge: dict[uuid.UUID | None, Decimal] = {}
    total_paid = ZERO
    for charge_id, amount in payments:
        total_paid += amount
        paid_by_charge[charge_id] = paid_by_charge.get(charge_id, ZERO) + amount

    total_charged = sum((c.amount for c in charges), ZERO)

    # Stamped here rather than in the router: the view is the moment the link
    # was actually used for something.
    access.last_used_at = now
    access.use_count += 1

    return PortalView(
        patient_name=f"{patient.first_name} {patient.last_name}",
        clinic_name=clinic.name,
        upcoming=upcoming,
        past=past,
        balance=money(total_charged - total_paid),
        charges=[
            PortalCharge(
                description=c.description,
                issued_on=c.issued_on,
                amount=money(c.amount),
                pending=money(c.amount - paid_by_charge.get(c.id, ZERO)),
            )
            for c in sorted(charges, key=lambda c: c.issued_on, reverse=True)
        ],
        expires_at=access.expires_at,
    )
