import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointments.models import Appointment
from app.modules.budgets.models import Budget, BudgetItem
from app.modules.patients.models import Patient
from app.modules.treatment_plans.models import TreatmentPlanItem


async def build_summary(db: AsyncSession, clinic_id: uuid.UUID, days: int = 7) -> dict:
    """Aggregates the dashboard reads from. Every figure is computed from real
    rows — nothing here is estimated or filled in when data is missing."""
    now = datetime.now(timezone.utc)
    today = now.date()
    window_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    window_end = window_start + timedelta(days=days)

    total_patients = await db.scalar(
        select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)
        )
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

    # Appointments per status over the window, for the donut.
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

    # Appointments per day over the window, for the bar chart. Days with no
    # appointments still appear, otherwise the chart would silently skip them.
    day_rows = (
        await db.execute(
            select(func.date(Appointment.starts_at), func.count(Appointment.id))
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.starts_at >= window_start,
                Appointment.starts_at < window_end,
                Appointment.status.notin_(["cancelada"]),
            )
            .group_by(func.date(Appointment.starts_at))
        )
    ).all()
    counts_by_day = {row[0]: row[1] for row in day_rows}
    per_day = [
        {"date": (today + timedelta(days=offset)).isoformat(), "count": counts_by_day.get(today + timedelta(days=offset), 0)}
        for offset in range(days)
    ]

    # Week-over-week comparison, computed from real rows rather than shown as
    # a decorative arrow: last 7 days against the 7 before them.
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

    # Budget money, split by whether the patient has answered yet.
    budget_totals = await _budget_totals_by_status(db, clinic_id)

    treatments_pending = await db.scalar(
        select(func.count(TreatmentPlanItem.id)).where(
            TreatmentPlanItem.clinic_id == clinic_id,
            TreatmentPlanItem.status.in_(["propuesto", "aprobado", "en_progreso"]),
        )
    )

    return {
        "total_patients": total_patients or 0,
        "new_patients_30d": new_patients_30d or 0,
        "appointments_today": appointments_today or 0,
        "appointments_this_week": appointments_this_week,
        "appointments_previous_week": appointments_previous_week,
        "treatments_pending": treatments_pending or 0,
        "appointments_by_status": [{"status": s, "count": c} for s, c in status_rows],
        "appointments_per_day": per_day,
        "budget_accepted_total": budget_totals["aceptado"],
        "budget_awaiting_total": budget_totals["awaiting"],
    }


async def _budget_totals_by_status(db: AsyncSession, clinic_id: uuid.UUID) -> dict[str, float]:
    """Budget totals are the sum of their line items; doing it in SQL keeps the
    dashboard from loading every budget just to add numbers up."""
    rows = (
        await db.execute(
            select(
                Budget.status,
                func.coalesce(
                    func.sum((BudgetItem.price - BudgetItem.discount) * BudgetItem.quantity), 0
                ),
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
