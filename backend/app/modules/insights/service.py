"""Oportunidades y huecos libres.

Nada de esto es estimado ni «inteligente»: son reglas claras sobre los datos de
la clínica, para que recepción sepa a quién llamar hoy y cuándo hay sitio en la
agenda. Cada lista dice por qué aparece cada paciente.
"""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointments.models import Appointment
from app.modules.clinics.models import Clinic
from app.modules.dashboard.service import _clinic_tz
from app.modules.patients.models import Patient
from app.modules.payments.models import Charge, Payment
from app.modules.privacy.models import DataConsent
from app.modules.professionals.models import Professional
from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
from app.modules.treatments.models import Treatment
from app.modules.payments.constants import money

ZERO = Decimal("0.00")
RECALL_MONTHS = 6
ACTIVE_STATUSES = ("programada", "confirmada", "en_espera", "en_atencion")
# Horario por defecto para buscar huecos. La agenda no guarda un horario por
# profesional, así que se usa la jornada típica de una consulta.
DAY_START = time(8, 0)
DAY_END = time(19, 0)
STEP_MINUTES = 15


def _name(p: Patient) -> str:
    return f"{p.first_name} {p.last_name}"


async def _revoked(db: AsyncSession, clinic_id: uuid.UUID, ids: set[uuid.UUID]) -> set[uuid.UUID]:
    """Pacientes cuya última decisión sobre comunicaciones fue «no»."""
    if not ids:
        return set()
    rows = (
        await db.execute(
            select(DataConsent.patient_id, DataConsent.granted, DataConsent.recorded_at)
            .where(
                DataConsent.clinic_id == clinic_id,
                DataConsent.kind == "comunicaciones",
                DataConsent.patient_id.in_(ids),
            )
            .order_by(DataConsent.recorded_at)
        )
    ).all()
    latest: dict[uuid.UUID, bool] = {}
    for pid, granted, _ in rows:
        latest[pid] = granted
    return {pid for pid, granted in latest.items() if granted is False}


def _contact(p: Patient, revoked: set[uuid.UUID]) -> dict:
    return {
        "patient_id": p.id,
        "patient_name": _name(p),
        "phone": p.phone,
        "whatsapp": p.whatsapp or p.phone,
        "contact_allowed": p.id not in revoked,
    }


async def opportunities(db: AsyncSession, clinic_id: uuid.UUID, include_money: bool) -> dict:
    tz = await _clinic_tz(db, clinic_id)
    now = datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    clinic_name = await db.scalar(select(Clinic.name).where(Clinic.id == clinic_id)) or "la clínica"

    patients = {
        p.id: p
        for p in (
            await db.execute(select(Patient).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)))
        )
        .scalars()
        .all()
    }

    # Quién tiene ya una cita por delante: no hace falta llamarle.
    with_future = set(
        (
            await db.execute(
                select(Appointment.patient_id).where(
                    Appointment.clinic_id == clinic_id,
                    Appointment.starts_at >= now,
                    Appointment.status.in_(ACTIVE_STATUSES),
                )
            )
        )
        .scalars()
        .all()
    )

    # ---- Pacientes por recuperar: última visita atendida hace 6+ meses.
    last_visits = dict(
        (
            await db.execute(
                select(Appointment.patient_id, func.max(Appointment.starts_at))
                .where(Appointment.clinic_id == clinic_id, Appointment.status == "atendida")
                .group_by(Appointment.patient_id)
            )
        ).all()
    )
    recall_raw = []
    for pid, last in last_visits.items():
        p = patients.get(pid)
        if p is None or pid in with_future:
            continue
        last_day = last.astimezone(tz).date()
        months = (today.year - last_day.year) * 12 + today.month - last_day.month
        if months >= RECALL_MONTHS:
            recall_raw.append((p, last_day, months))
    recall_raw.sort(key=lambda r: r[1])

    # ---- Tratamientos aprobados o en curso sin cita futura.
    plan_rows = (
        await db.execute(
            select(TreatmentPlan.patient_id, Treatment.name, TreatmentPlanItem.price, TreatmentPlanItem.discount)
            .join(TreatmentPlanItem, TreatmentPlanItem.plan_id == TreatmentPlan.id)
            .join(Treatment, Treatment.id == TreatmentPlanItem.treatment_id)
            .where(
                TreatmentPlan.clinic_id == clinic_id,
                TreatmentPlanItem.status.in_(("aprobado", "en_progreso")),
            )
        )
    ).all()
    pending: dict[uuid.UUID, tuple[list[str], Decimal]] = {}
    for pid, name, price, discount in plan_rows:
        if pid in with_future or pid not in patients:
            continue
        names, total = pending.get(pid, ([], ZERO))
        names.append(name)
        pending[pid] = (names, total + Decimal(price or 0) - Decimal(discount or 0))

    # ---- Deudores (solo para quien puede ver cobros).
    debtors_raw: list[tuple[Patient, Decimal, date]] = []
    if include_money:
        charges = (
            await db.execute(select(Charge).where(Charge.clinic_id == clinic_id, Charge.voided_at.is_(None)))
        ).scalars().all()
        paid: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO)
        for cid, amount in (
            await db.execute(
                select(Payment.charge_id, Payment.amount).where(
                    Payment.clinic_id == clinic_id, Payment.voided_at.is_(None), Payment.charge_id.is_not(None)
                )
            )
        ).all():
            paid[cid] += amount
        owed: dict[uuid.UUID, tuple[Decimal, date]] = {}
        for c in charges:
            rest = money(c.amount - paid.get(c.id, ZERO))
            if rest <= ZERO:
                continue
            total, oldest = owed.get(c.patient_id, (ZERO, c.issued_on))
            owed[c.patient_id] = (total + rest, min(oldest, c.issued_on))
        debtors_raw = [(patients[pid], money(t), d) for pid, (t, d) in owed.items() if pid in patients]
        debtors_raw.sort(key=lambda r: r[1], reverse=True)

    # ---- Cumpleaños en los próximos 7 días.
    birthdays_raw = []
    for p in patients.values():
        if p.birth_date is None:
            continue
        try:
            this_year = p.birth_date.replace(year=today.year)
        except ValueError:  # 29 de febrero
            this_year = date(today.year, 3, 1)
        if this_year < today:
            try:
                this_year = p.birth_date.replace(year=today.year + 1)
            except ValueError:
                this_year = date(today.year + 1, 3, 1)
        days_until = (this_year - today).days
        if days_until <= 7:
            birthdays_raw.append((p, this_year.year - p.birth_date.year, days_until))
    birthdays_raw.sort(key=lambda r: r[2])

    # ---- Citas de mañana sin confirmar.
    tomorrow = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz)
    unconfirmed_rows = (
        await db.execute(
            select(Appointment, Professional)
            .join(Professional, Professional.id == Appointment.professional_id)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.starts_at >= tomorrow,
                Appointment.starts_at < tomorrow + timedelta(days=1),
                Appointment.status == "programada",
            )
            .order_by(Appointment.starts_at)
        )
    ).all()

    involved = (
        {r[0].id for r in recall_raw}
        | set(pending)
        | {r[0].id for r in debtors_raw}
        | {r[0].id for r in birthdays_raw}
        | {a.patient_id for a, _ in unconfirmed_rows}
    )
    revoked = await _revoked(db, clinic_id, involved)

    return {
        "clinic_name": clinic_name,
        "recall": [
            {**_contact(p, revoked), "last_visit": last, "months_since": months}
            for p, last, months in recall_raw[:50]
        ],
        "pending_treatments": [
            {**_contact(patients[pid], revoked), "treatments": names, "amount": money(total)}
            for pid, (names, total) in sorted(pending.items(), key=lambda kv: kv[1][1], reverse=True)[:50]
        ],
        "debtors": [
            {**_contact(p, revoked), "pending": total, "oldest_charge_on": oldest}
            for p, total, oldest in debtors_raw[:50]
        ],
        "birthdays": [
            {**_contact(p, revoked), "birth_date": p.birth_date, "turns": turns, "days_until": days}
            for p, turns, days in birthdays_raw
        ],
        "unconfirmed": [
            {
                **_contact(patients[a.patient_id], revoked),
                "appointment_id": a.id,
                "starts_at": a.starts_at,
                "professional_name": f"{prof.first_name} {prof.last_name}",
            }
            for a, prof in unconfirmed_rows
            if a.patient_id in patients
        ],
    }


async def free_slots(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    professional_id: uuid.UUID,
    duration: int,
    start_day: date | None,
    days: int,
    limit: int,
) -> list[dict]:
    """Primeros huecos donde cabe una cita de `duration` minutos para el
    profesional, de lunes a sábado en horario de consulta, sin pisar sus citas
    activas. Las horas pasadas de hoy no cuentan."""
    tz = await _clinic_tz(db, clinic_id)
    now = datetime.now(timezone.utc)
    first = start_day or now.astimezone(tz).date()
    window_start = datetime.combine(first, time.min, tzinfo=tz)
    window_end = window_start + timedelta(days=days)

    busy = (
        await db.execute(
            select(Appointment.starts_at, Appointment.ends_at).where(
                Appointment.clinic_id == clinic_id,
                Appointment.professional_id == professional_id,
                Appointment.starts_at < window_end,
                Appointment.ends_at > window_start,
                Appointment.status.notin_(("cancelada", "no_asistio")),
            )
        )
    ).all()

    length = timedelta(minutes=duration)
    step = timedelta(minutes=STEP_MINUTES)
    slots: list[dict] = []
    for offset in range(days):
        day = first + timedelta(days=offset)
        if day.weekday() == 6:  # domingo
            continue
        cursor = datetime.combine(day, DAY_START, tzinfo=tz)
        close = datetime.combine(day, DAY_END, tzinfo=tz)
        while cursor + length <= close:
            end = cursor + length
            if cursor > now and not any(s < end and e > cursor for s, e in busy):
                slots.append({"starts_at": cursor.astimezone(timezone.utc), "ends_at": end.astimezone(timezone.utc)})
                if len(slots) >= limit:
                    return slots
                # Un hueco por media hora basta para elegir; no 4 seguidos.
                cursor = end if duration >= 30 else cursor + timedelta(minutes=30)
                continue
            cursor += step
    return slots
