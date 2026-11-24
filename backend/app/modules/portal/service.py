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
from app.modules.payment_accounts.service import list_accounts as list_payment_accounts
from app.modules.portal.schemas import (
    PortalAppointment,
    PortalCharge,
    PortalComparacion,
    PortalComprobante,
    PortalCuota,
    PortalHallazgo,
    PortalOrtho,
    PortalPaymentAccount,
    PortalPlanItem,
    PortalView,
)

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
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, include_clinical: bool = False
) -> tuple[PortalAccess, str]:
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
        include_clinical=include_clinical,
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
                id=c.id,
                description=c.description,
                issued_on=c.issued_on,
                amount=money(c.amount),
                pending=money(c.amount - paid_by_charge.get(c.id, ZERO)),
            )
            for c in sorted(charges, key=lambda c: c.issued_on, reverse=True)
        ],
        expires_at=access.expires_at,
        payment_accounts=[
            PortalPaymentAccount.model_validate(a)
            for a in await list_payment_accounts(db, clinic.id, only_active=True)
        ],
        **await extras(db, clinic, patient.id, access.include_clinical),
    )


async def extras(db: AsyncSession, clinic: Clinic, patient_id: uuid.UUID, clinica: bool) -> dict:
    from app.modules.imaging.comparisons import ImageComparison
    from app.modules.imaging.models import ClinicalImage
    from app.modules.odontogram.models import Odontogram, ToothCondition
    from app.modules.portal.comprobantes import a_salida, del_paciente
    from app.modules.treatment_plans.constants import TREATMENT_PLAN_ITEM_STATUSES
    from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
    from app.modules.treatments.models import Treatment

    out: dict = {"incluye_clinica": clinica}
    out["comprobantes"] = [
        PortalComprobante(**c.model_dump(include={"id", "amount", "paid_on", "destino", "status", "status_label", "reject_reason", "created_at"}))
        for c in await a_salida(db, await del_paciente(db, clinic.id, patient_id))
    ]
    if clinic.orthodontics_enabled:
        from datetime import date as _date

        from app.modules.orthodontics.service import _case_out, _get_case, _payments_by_charge, list_cases

        casos = (await list_cases(db, clinic.id, patient_id=patient_id, include_closed=True)).items
        vigente = next((c for c in casos if c.status in ("activo", "retencion", "pausa")), casos[0] if casos else None)
        if vigente:
            caso = await _get_case(db, clinic.id, vigente.id)
            pagos = (await _payments_by_charge(db, [caso.charge_id] if caso.charge_id else [])).get(caso.charge_id, [])
            paciente = await db.get(Patient, patient_id)
            d = _case_out(caso, paciente, None, pagos, _date.today(), detail=True)
            atendidos = sum(1 for c in d.controls if c.attended_on)
            total = max(len(d.controls), d.estimated_months or 0)
            out["ortodoncia"] = PortalOrtho(
                code=d.code, appliance=d.appliance, started_on=d.started_on, estimated_months=d.estimated_months,
                status=d.status, controls_attended=atendidos, controls_total=total,
                progress=(min(1.0, atendidos / total) if total else None),
                next_control_on=d.next_control_on, next_control_overdue=d.next_control_overdue,
                agreed_total=d.agreed_total, paid=d.paid, balance=d.balance,
                cuotas=[
                    PortalCuota(
                        id=c.id, number=c.number, planned_on=c.planned_on, attended_on=c.attended_on,
                        amount=c.amount, paid=c.paid, balance=c.balance, status=c.status,
                    )
                    for c in d.controls
                ],
            )

    if not clinica:
        return out

    etiquetas = dict(TREATMENT_PLAN_ITEM_STATUSES)
    out["plan"] = [
        PortalPlanItem(treatment=nombre, fdi_number=fdi, status=estado, status_label=etiquetas.get(estado, estado))
        for nombre, fdi, estado in (
            await db.execute(
                select(Treatment.name, TreatmentPlanItem.fdi_number, TreatmentPlanItem.status)
                .join(TreatmentPlanItem, TreatmentPlanItem.treatment_id == Treatment.id)
                .join(TreatmentPlan, TreatmentPlan.id == TreatmentPlanItem.plan_id)
                .where(
                    TreatmentPlan.clinic_id == clinic.id,
                    TreatmentPlan.patient_id == patient_id,
                    TreatmentPlan.cancelled_at.is_(None),
                    TreatmentPlanItem.status.in_(("propuesto", "aprobado", "en_progreso", "completado")),
                )
                .order_by(TreatmentPlan.created_at.desc())
            )
        ).all()
    ][:40]

    ultimo = await db.scalar(
        select(Odontogram.id)
        .where(Odontogram.clinic_id == clinic.id, Odontogram.patient_id == patient_id)
        .order_by(Odontogram.created_at.desc())
        .limit(1)
    )
    if ultimo:
        out["odontograma"] = [
            PortalHallazgo(fdi_number=f, surface=s, condition=c)
            for f, s, c in (
                await db.execute(
                    select(ToothCondition.fdi_number, ToothCondition.surface, ToothCondition.condition).where(
                        ToothCondition.odontogram_id == ultimo
                    )
                )
            ).all()
        ]

    vivas = select(ClinicalImage.id).where(ClinicalImage.patient_id == patient_id, ClinicalImage.archived_at.is_(None))
    out["comparaciones"] = [
        PortalComparacion(id=c.id, title=c.title, treatment=c.treatment, before_id=c.before_image_id, after_id=c.after_image_id)
        for c in (
            await db.execute(
                select(ImageComparison)
                .where(
                    ImageComparison.clinic_id == clinic.id,
                    ImageComparison.patient_id == patient_id,
                    ImageComparison.before_image_id.in_(vivas),
                    ImageComparison.after_image_id.in_(vivas),
                )
                .order_by(ImageComparison.created_at.desc())
            )
        ).scalars().all()
    ]
    return out


async def imagen_del_portal(db: AsyncSession, access: PortalAccess, image_id: uuid.UUID):
    from app.modules.imaging.comparisons import ImageComparison
    from app.modules.imaging.models import ClinicalImage
    from app.shared.storage import get_storage

    if not access.include_clinical:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    usada = await db.scalar(
        select(ImageComparison.id).where(
            ImageComparison.patient_id == access.patient_id,
            ImageComparison.clinic_id == access.clinic_id,
            (ImageComparison.before_image_id == image_id) | (ImageComparison.after_image_id == image_id),
        ).limit(1)
    )
    imagen = await db.get(ClinicalImage, image_id)
    if not usada or imagen is None or imagen.archived_at is not None or imagen.patient_id != access.patient_id:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return imagen, await get_storage().read(imagen.storage_key)
