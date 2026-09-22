import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.appointments.models import Appointment
from app.modules.budgets.models import Budget, BudgetItem
from app.modules.clinics.models import Clinic
from app.modules.patients.models import Patient
from app.modules.treatment_plans.models import TreatmentPlanItem

ZERO = Decimal("0.00")


async def _clinic_tz(db: AsyncSession, clinic_id: uuid.UUID) -> ZoneInfo:
    name = await db.scalar(select(Clinic.timezone).where(Clinic.id == clinic_id))
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


async def build_summary(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    days: int = 7,
    can=lambda _permission: True,
) -> dict:
    """Aggregates the dashboard reads from. Every figure is computed from real
    rows — nothing here is estimated or filled in when data is missing.

    "Hoy" es el día de la clínica, no el de UTC: en Ecuador, a las 20:00 UTC ya
    es mañana, y el panel enseñaría la agenda del día siguiente."""
    tz = await _clinic_tz(db, clinic_id)
    now = datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    window_start = datetime.combine(today, time.min, tzinfo=tz)
    window_end = window_start + timedelta(days=days)
    tz_name = str(tz.key)

    total_patients = await db.scalar(
        select(func.count(Patient.id)).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None))
    )
    new_patients_30d = await db.scalar(
        select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
            Patient.created_at >= now - timedelta(days=30),
        )
    )

    appointments_today = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.starts_at >= window_start,
            Appointment.starts_at < window_start + timedelta(days=1),
            Appointment.status.notin_(["cancelada"]),
        )
    )

    status_rows = (
        await db.execute(
            select(Appointment.status, func.count(Appointment.id))
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.starts_at >= window_start,
                Appointment.starts_at < window_end,
            )
            .group_by(Appointment.status)
        )
    ).all()

    # Agrupado por el día local de la clínica. Days with no appointments still
    # appear, otherwise the chart would silently skip them.
    local_day = func.date(func.timezone(tz_name, Appointment.starts_at))
    day_rows = (
        await db.execute(
            select(local_day, func.count(Appointment.id))
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.starts_at >= window_start,
                Appointment.starts_at < window_end,
                Appointment.status.notin_(["cancelada"]),
            )
            .group_by(local_day)
        )
    ).all()
    counts_by_day = {row[0]: row[1] for row in day_rows}
    per_day = [
        {
            "date": (today + timedelta(days=offset)).isoformat(),
            "count": counts_by_day.get(today + timedelta(days=offset), 0),
        }
        for offset in range(days)
    ]

    appointments_this_week = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.starts_at >= now - timedelta(days=7),
            Appointment.starts_at < now,
            Appointment.status.notin_(["cancelada"]),
        )
    ) or 0
    appointments_previous_week = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.starts_at >= now - timedelta(days=14),
            Appointment.starts_at < now - timedelta(days=7),
            Appointment.status.notin_(["cancelada"]),
        )
    ) or 0

    treatments_pending = await db.scalar(
        select(func.count(TreatmentPlanItem.id)).where(
            TreatmentPlanItem.clinic_id == clinic_id,
            TreatmentPlanItem.status.in_(["propuesto", "aprobado", "en_progreso"]),
        )
    )

    today_agenda = None
    if can("appointments:read"):
        today_agenda = await _today_agenda(db, clinic_id, window_start)

    budget_totals = await _budget_totals_by_status(db, clinic_id) if can("budgets:read") else None

    income_month = income_prev = receivables = None
    if can("payments:read"):
        income_month, income_prev = await _income(db, clinic_id, today)
        from app.modules.reports.service import _receivables

        receivables, _ = await _receivables(db, clinic_id)

    return {
        "today": today.isoformat(),
        "total_patients": total_patients or 0,
        "new_patients_30d": new_patients_30d or 0,
        "appointments_today": appointments_today or 0,
        "appointments_this_week": appointments_this_week,
        "appointments_previous_week": appointments_previous_week,
        "treatments_pending": treatments_pending or 0,
        "appointments_by_status": [{"status": s, "count": c} for s, c in status_rows],
        "appointments_per_day": per_day,
        "today_agenda": today_agenda,
        "budget_accepted_total": budget_totals["aceptado"] if budget_totals else None,
        "budget_awaiting_total": budget_totals["awaiting"] if budget_totals else None,
        "income_month": str(income_month) if income_month is not None else None,
        "income_previous_month_same_period": str(income_prev) if income_prev is not None else None,
        "receivables_total": str(receivables) if receivables is not None else None,
        "attention": await _attention(db, clinic_id, today, can, budget_totals),
    }


async def _today_agenda(db: AsyncSession, clinic_id: uuid.UUID, day_start: datetime) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(Appointment)
                .options(
                    selectinload(Appointment.patient),
                    selectinload(Appointment.professional),
                    selectinload(Appointment.treatment),
                )
                .where(
                    Appointment.clinic_id == clinic_id,
                    Appointment.starts_at >= day_start,
                    Appointment.starts_at < day_start + timedelta(days=1),
                    Appointment.status.notin_(["cancelada"]),
                )
                .order_by(Appointment.starts_at)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": a.id,
            "starts_at": a.starts_at,
            "ends_at": a.ends_at,
            "status": a.status,
            "patient_id": a.patient_id,
            "patient_name": f"{a.patient.first_name} {a.patient.last_name}",
            "professional_name": f"{a.professional.first_name} {a.professional.last_name}",
            "professional_color": a.professional.color_hex,
            "treatment_name": a.treatment.name if a.treatment else None,
        }
        for a in rows
    ]


async def _income(db: AsyncSession, clinic_id: uuid.UUID, today: date) -> tuple[Decimal, Decimal]:
    """Lo cobrado este mes, y lo cobrado el mes pasado hasta el mismo día: comparar
    un mes a medias contra uno entero haría parecer que siempre se va a peor."""
    from app.modules.payments.models import Payment

    month_start = today.replace(day=1)
    prev_end = month_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    prev_same_day = prev_start.replace(day=min(today.day, prev_end.day))

    async def total(start: date, end: date) -> Decimal:
        value = await db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.clinic_id == clinic_id,
                Payment.voided_at.is_(None),
                Payment.received_on >= start,
                Payment.received_on <= end,
            )
        )
        return Decimal(value or 0).quantize(ZERO)

    return await total(month_start, today), await total(prev_start, prev_same_day)


async def _attention(
    db: AsyncSession, clinic_id: uuid.UUID, today: date, can, budget_totals: dict | None
) -> dict:
    stock_alerts = None
    if can("inventory:read"):
        from app.modules.inventory.service import get_alerts

        alerts = await get_alerts(db, clinic_id)
        stock_alerts = len(
            {i.id for i in alerts.below_minimum} | {i.id for i in alerts.expiring_soon} | {i.id for i in alerts.expired}
        )

    lab_overdue = None
    if can("laboratory:read"):
        from app.modules.laboratory.constants import TERMINAL_STATUSES
        from app.modules.laboratory.models import LabOrder

        lab_overdue = await db.scalar(
            select(func.count(LabOrder.id)).where(
                LabOrder.clinic_id == clinic_id,
                LabOrder.status.not_in(tuple(TERMINAL_STATUSES)),
                LabOrder.received_on.is_(None),
                LabOrder.due_on < today,
            )
        ) or 0

    budgets_awaiting = None
    if budget_totals is not None:
        budgets_awaiting = await db.scalar(
            select(func.count(Budget.id)).where(
                Budget.clinic_id == clinic_id, Budget.status.in_(["enviado", "visto"])
            )
        ) or 0

    birthdays = None
    if can("patients:read"):
        rows = (
            await db.execute(
                select(Patient).where(
                    Patient.clinic_id == clinic_id,
                    Patient.deleted_at.is_(None),
                    extract("month", Patient.birth_date) == today.month,
                    extract("day", Patient.birth_date) == today.day,
                )
            )
        ).scalars().all()
        birthdays = [
            {
                "patient_id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "turns": today.year - p.birth_date.year,
                "whatsapp": p.whatsapp or p.phone,
            }
            for p in rows
        ]

    return {
        "stock_alerts": stock_alerts,
        "lab_overdue": lab_overdue,
        "budgets_awaiting": budgets_awaiting,
        "birthdays": birthdays,
    }


async def _budget_totals_by_status(db: AsyncSession, clinic_id: uuid.UUID) -> dict[str, float]:
    """Budget totals are the sum of their line items; doing it in SQL keeps the
    dashboard from loading every budget just to add numbers up."""
    rows = (
        await db.execute(
            select(
                Budget.status,
                func.coalesce(func.sum((BudgetItem.price - BudgetItem.discount) * BudgetItem.quantity), 0),
            )
            .join(BudgetItem, BudgetItem.budget_id == Budget.id)
            .where(Budget.clinic_id == clinic_id)
            .group_by(Budget.status)
        )
    ).all()

    totals = {"aceptado": 0.0, "awaiting": 0.0}
    for status, amount in rows:
        if status == "aceptado":
            totals["aceptado"] += float(amount)
        elif status in ("enviado", "visto"):
            totals["awaiting"] += float(amount)
    return totals
