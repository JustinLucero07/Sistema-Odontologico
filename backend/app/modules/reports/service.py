import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.appointments.models import Appointment
from app.modules.budgets.models import Budget
from app.modules.diagnoses.models import Diagnosis
from app.modules.patients.models import Patient
from app.modules.payments.constants import PAYMENT_METHODS, money
from app.modules.payments.models import Charge, Payment
from app.modules.professionals.models import Professional
from app.modules.reports.schemas import (
    AgingBucket,
    AppointmentReport,
    BudgetConversion,
    ClinicalReport,
    DateRange,
    FinancialReport,
    NamedAmount,
    PatientReport,
    ReportSummary,
)
from app.modules.treatment_plans.models import TreatmentPlanItem
from app.modules.treatments.models import Treatment

ZERO = Decimal("0.00")
_METHOD_LABELS = {code: label for code, label, _ in PAYMENT_METHODS}

APPOINTMENT_LABELS = {
    "programada": "Programada",
    "confirmada": "Confirmada",
    "en_espera": "En espera",
    "en_atencion": "En atención",
    "atendida": "Atendida",
    "cancelada": "Cancelada",
    "no_asistio": "No asistió",
}

WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Buckets are by how long a debt has been outstanding, counted from the day it
# was billed. 90+ is where a clinic normally stops expecting to be paid.
AGING_BUCKETS = [(0, 30, "0–30 días"), (31, 60, "31–60 días"), (61, 90, "61–90 días")]
AGING_OVERFLOW = "Más de 90 días"


def _window(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    """A day range as an inclusive instant range, so an appointment at 23:50 on
    the last day is inside the report rather than just outside it."""
    return (
        datetime.combine(date_from, time.min, tzinfo=timezone.utc),
        datetime.combine(date_to, time.max, tzinfo=timezone.utc),
    )


def _rate(numerator: int, denominator: int) -> float | None:
    """None, not zero, when there is nothing to divide. A clinic with no
    concluded appointments has an UNKNOWN no-show rate, not a perfect one."""
    return round(numerator / denominator * 100, 1) if denominator else None


async def _professional_names(db: AsyncSession, clinic_id: uuid.UUID) -> dict[uuid.UUID, str]:
    result = await db.execute(
        select(Professional.id, Professional.first_name, Professional.last_name).where(
            Professional.clinic_id == clinic_id
        )
    )
    return {pid: f"{first} {last}" for pid, first, last in result.all()}


# ---- Financial ----------------------------------------------------------


async def financial_report(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> FinancialReport:
    payments = list(
        (
            await db.execute(
                select(Payment).where(
                    Payment.clinic_id == clinic_id,
                    Payment.received_on >= date_from,
                    Payment.received_on <= date_to,
                )
            )
        )
        .scalars()
        .all()
    )
    live = [p for p in payments if p.voided_at is None]
    voided = [p for p in payments if p.voided_at is not None]

    by_method: dict[str, list[Payment]] = defaultdict(list)
    for payment in live:
        by_method[payment.method].append(payment)

    # Money is attributed to the professional who did the work, through the
    # charge's budget. A payment on account has no professional, and is left
    # out rather than spread across everyone.
    charge_professional: dict[uuid.UUID, uuid.UUID] = {}
    charge_rows = (
        await db.execute(
            select(Charge.id, TreatmentPlanItem.professional_id)
            .join(Budget, Charge.budget_id == Budget.id)
            .join(TreatmentPlanItem, TreatmentPlanItem.plan_id == Budget.treatment_plan_id)
            .where(Charge.clinic_id == clinic_id)
        )
    ).all()
    for charge_id, professional_id in charge_rows:
        if professional_id is not None:
            charge_professional.setdefault(charge_id, professional_id)

    names = await _professional_names(db, clinic_id)
    per_professional: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for payment in live:
        professional_id = charge_professional.get(payment.charge_id) if payment.charge_id else None
        if professional_id is not None:
            per_professional[professional_id].append(payment)

    daily_totals: dict[date, Decimal] = defaultdict(lambda: ZERO)
    for payment in live:
        daily_totals[payment.received_on] += payment.amount

    charges_in_range = list(
        (
            await db.execute(
                select(Charge).where(
                    Charge.clinic_id == clinic_id,
                    Charge.issued_on >= date_from,
                    Charge.issued_on <= date_to,
                    Charge.voided_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    outstanding, aging = await _receivables(db, clinic_id)

    return FinancialReport(
        range=DateRange(date_from=date_from, date_to=date_to),
        collected=money(sum((p.amount for p in live), ZERO)),
        charged=money(sum((c.amount for c in charges_in_range), ZERO)),
        payment_count=len(live),
        by_method=sorted(
            (
                NamedAmount(
                    key=code,
                    label=_METHOD_LABELS.get(code, code),
                    amount=money(sum((p.amount for p in items), ZERO)),
                    count=len(items),
                )
                for code, items in by_method.items()
            ),
            key=lambda n: n.amount,
            reverse=True,
        ),
        by_professional=sorted(
            (
                NamedAmount(
                    key=str(pid),
                    label=names.get(pid, "—"),
                    amount=money(sum((p.amount for p in items), ZERO)),
                    count=len(items),
                )
                for pid, items in per_professional.items()
            ),
            key=lambda n: n.amount,
            reverse=True,
        ),
        daily=[
            {"day": day.isoformat(), "amount": str(money(total))}
            for day, total in sorted(daily_totals.items())
        ],
        outstanding_total=outstanding,
        aging=aging,
        voided_total=money(sum((p.amount for p in voided), ZERO)),
        voided_count=len(voided),
    )


async def _receivables(
    db: AsyncSession, clinic_id: uuid.UUID
) -> tuple[Decimal, list[AgingBucket]]:
    """What is still owed, bucketed by age. Computed from live charges minus
    the payments that still stand, so a voided payment re-opens its debt."""
    charges = list(
        (
            await db.execute(
                select(Charge).where(Charge.clinic_id == clinic_id, Charge.voided_at.is_(None))
            )
        )
        .scalars()
        .all()
    )
    paid_by_charge: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO)
    payments = (
        await db.execute(
            select(Payment.charge_id, Payment.amount).where(
                Payment.clinic_id == clinic_id,
                Payment.voided_at.is_(None),
                Payment.charge_id.is_not(None),
            )
        )
    ).all()
    for charge_id, amount in payments:
        paid_by_charge[charge_id] += amount

    today = date.today()
    buckets: dict[str, list[Decimal]] = {label: [] for _, _, label in AGING_BUCKETS}
    buckets[AGING_OVERFLOW] = []
    total = ZERO

    for charge in charges:
        pending = money(charge.amount - paid_by_charge.get(charge.id, ZERO))
        if pending <= ZERO:
            continue
        total += pending
        age = (today - charge.issued_on).days
        label = next((l for lo, hi, l in AGING_BUCKETS if lo <= age <= hi), AGING_OVERFLOW)
        buckets[label].append(pending)

    return money(total), [
        AgingBucket(label=label, amount=money(sum(values, ZERO)), count=len(values))
        for label, values in buckets.items()
    ]


# ---- Clinical -----------------------------------------------------------


async def clinical_report(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> ClinicalReport:
    rows = (
        await db.execute(
            select(TreatmentPlanItem, Treatment.name)
            .join(Treatment, TreatmentPlanItem.treatment_id == Treatment.id)
            .where(
                TreatmentPlanItem.clinic_id == clinic_id,
                TreatmentPlanItem.status == "completado",
                TreatmentPlanItem.completed_date >= date_from,
                TreatmentPlanItem.completed_date <= date_to,
            )
        )
    ).all()

    by_treatment: dict[str, list[TreatmentPlanItem]] = defaultdict(list)
    by_professional: dict[uuid.UUID | None, list[TreatmentPlanItem]] = defaultdict(list)
    for item, treatment_name in rows:
        by_treatment[treatment_name].append(item)
        by_professional[item.professional_id].append(item)

    names = await _professional_names(db, clinic_id)

    diagnosis_rows = (
        await db.execute(
            select(Diagnosis.description).where(
                Diagnosis.clinic_id == clinic_id,
                Diagnosis.created_at >= _window(date_from, date_to)[0],
                Diagnosis.created_at <= _window(date_from, date_to)[1],
            )
        )
    ).all()
    diagnosis_counts: dict[str, int] = defaultdict(int)
    for (description,) in diagnosis_rows:
        diagnosis_counts[(description or "Sin descripción").strip()[:80]] += 1

    return ClinicalReport(
        range=DateRange(date_from=date_from, date_to=date_to),
        treatments_completed=len(rows),
        by_treatment=sorted(
            (
                NamedAmount(
                    key=name,
                    label=name,
                    amount=money(sum((Decimal(str(i.net_price)) for i in items), ZERO)),
                    count=len(items),
                )
                for name, items in by_treatment.items()
            ),
            key=lambda n: n.count,
            reverse=True,
        )[:15],
        by_professional=sorted(
            (
                NamedAmount(
                    key=str(pid) if pid else "sin_asignar",
                    label=names.get(pid, "Sin asignar") if pid else "Sin asignar",
                    amount=money(sum((Decimal(str(i.net_price)) for i in items), ZERO)),
                    count=len(items),
                )
                for pid, items in by_professional.items()
            ),
            key=lambda n: n.amount,
            reverse=True,
        ),
        top_diagnoses=sorted(
            (
                NamedAmount(key=text, label=text, amount=ZERO, count=count)
                for text, count in diagnosis_counts.items()
            ),
            key=lambda n: n.count,
            reverse=True,
        )[:10],
        budgets=await _budget_conversion(db, clinic_id, date_from, date_to),
    )


async def _budget_conversion(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> BudgetConversion:
    start, end = _window(date_from, date_to)
    budgets = list(
        (
            await db.execute(
                # `Budget.total` walks its items, so they have to be loaded
                # here: reaching a lazy relationship from a property later
                # means IO outside the async context, which simply fails.
                select(Budget)
                .options(selectinload(Budget.items))
                .where(
                    Budget.clinic_id == clinic_id,
                    Budget.created_at >= start,
                    Budget.created_at <= end,
                )
            )
        )
        .scalars()
        .all()
    )
    # `total` is a Python property, so the grouping happens here rather than in
    # SQL; budget volumes per period are small enough that this is fine.
    groups: dict[str, list[Budget]] = defaultdict(list)
    for budget in budgets:
        if budget.status == "aceptado":
            groups["accepted"].append(budget)
        elif budget.status == "rechazado":
            groups["rejected"].append(budget)
        else:
            groups["pending"].append(budget)

    accepted, rejected, pending = (
        groups["accepted"],
        groups["rejected"],
        groups["pending"],
    )
    decided = len(accepted) + len(rejected)

    def total_of(items: list[Budget]) -> Decimal:
        return money(sum((Decimal(str(b.total)) for b in items), ZERO))

    return BudgetConversion(
        accepted_count=len(accepted),
        accepted_amount=total_of(accepted),
        rejected_count=len(rejected),
        rejected_amount=total_of(rejected),
        pending_count=len(pending),
        pending_amount=total_of(pending),
        conversion_rate=_rate(len(accepted), decided),
    )


# ---- Appointments -------------------------------------------------------


async def appointment_report(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> AppointmentReport:
    start, end = _window(date_from, date_to)
    appointments = list(
        (
            await db.execute(
                select(Appointment).where(
                    Appointment.clinic_id == clinic_id,
                    Appointment.starts_at >= start,
                    Appointment.starts_at <= end,
                )
            )
        )
        .scalars()
        .all()
    )

    by_status: dict[str, int] = defaultdict(int)
    by_professional: dict[uuid.UUID, int] = defaultdict(int)
    by_weekday: dict[int, int] = defaultdict(int)
    for appointment in appointments:
        by_status[appointment.status] += 1
        by_professional[appointment.professional_id] += 1
        by_weekday[appointment.starts_at.weekday()] += 1

    attended = by_status.get("atendida", 0)
    no_show = by_status.get("no_asistio", 0)
    cancelled = by_status.get("cancelada", 0)
    # Only appointments whose outcome is known count toward the rates. A slot
    # still marked "programada" has not failed to happen — it has not happened.
    concluded = attended + no_show + cancelled

    names = await _professional_names(db, clinic_id)

    return AppointmentReport(
        range=DateRange(date_from=date_from, date_to=date_to),
        total=len(appointments),
        by_status=[
            NamedAmount(key=code, label=label, amount=ZERO, count=by_status.get(code, 0))
            for code, label in APPOINTMENT_LABELS.items()
            if by_status.get(code, 0) > 0
        ],
        by_professional=sorted(
            (
                NamedAmount(key=str(pid), label=names.get(pid, "—"), amount=ZERO, count=count)
                for pid, count in by_professional.items()
            ),
            key=lambda n: n.count,
            reverse=True,
        ),
        by_weekday=[
            NamedAmount(key=str(i), label=WEEKDAYS[i], amount=ZERO, count=by_weekday.get(i, 0))
            for i in range(7)
        ],
        concluded=concluded,
        attended=attended,
        no_show=no_show,
        cancelled=cancelled,
        no_show_rate=_rate(no_show, concluded),
        cancellation_rate=_rate(cancelled, concluded),
    )


# ---- Patients -----------------------------------------------------------


AGE_BANDS = [(0, 11, "0–11"), (12, 17, "12–17"), (18, 34, "18–34"), (35, 54, "35–54"), (55, 200, "55+")]
SEX_LABELS = {"M": "Masculino", "F": "Femenino", "O": "Otro"}


async def patient_report(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> PatientReport:
    start, end = _window(date_from, date_to)
    all_patients = list(
        (
            await db.execute(
                select(Patient).where(
                    Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    new_patients = [p for p in all_patients if start <= p.created_at <= end]

    by_month: dict[str, int] = defaultdict(int)
    for patient in new_patients:
        by_month[patient.created_at.strftime("%Y-%m")] += 1

    by_sex: dict[str, int] = defaultdict(int)
    by_band: dict[str, int] = defaultdict(int)
    today = date.today()
    for patient in all_patients:
        by_sex[patient.sex or "O"] += 1
        if patient.birth_date:
            age = (today - patient.birth_date).days // 365
            label = next((l for lo, hi, l in AGE_BANDS if lo <= age <= hi), "55+")
            by_band[label] += 1
        else:
            by_band["Sin fecha"] += 1

    # "Active" means seen in the last year. A patient with no visit for longer
    # is dormant, which is the list a clinic runs a recall campaign from.
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    seen_rows = (
        await db.execute(
            select(Appointment.patient_id)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.status == "atendida",
                Appointment.starts_at >= cutoff,
            )
            .distinct()
        )
    ).all()
    seen_recently = {row[0] for row in seen_rows}

    return PatientReport(
        range=DateRange(date_from=date_from, date_to=date_to),
        new_patients=len(new_patients),
        total_active=len(all_patients),
        by_month=[
            NamedAmount(key=month, label=month, amount=ZERO, count=count)
            for month, count in sorted(by_month.items())
        ],
        by_sex=[
            NamedAmount(key=code, label=SEX_LABELS.get(code, code), amount=ZERO, count=count)
            for code, count in sorted(by_sex.items())
        ],
        by_age_band=[
            NamedAmount(key=label, label=label, amount=ZERO, count=by_band[label])
            for _, _, label in AGE_BANDS
            if by_band.get(label)
        ]
        + ([NamedAmount(key="Sin fecha", label="Sin fecha de nacimiento", amount=ZERO, count=by_band["Sin fecha"])] if by_band.get("Sin fecha") else []),
        seen_last_12m=len(seen_recently),
        dormant=len(all_patients) - len(seen_recently),
    )


# ---- Summary ------------------------------------------------------------


async def summary(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> ReportSummary:
    financial = await financial_report(db, clinic_id, date_from, date_to)
    appointments = await appointment_report(db, clinic_id, date_from, date_to)
    patients = await patient_report(db, clinic_id, date_from, date_to)
    clinical = await clinical_report(db, clinic_id, date_from, date_to)

    return ReportSummary(
        range=DateRange(date_from=date_from, date_to=date_to),
        collected=financial.collected,
        outstanding=financial.outstanding_total,
        appointments=appointments.total,
        no_show_rate=appointments.no_show_rate,
        new_patients=patients.new_patients,
        treatments_completed=clinical.treatments_completed,
    )
