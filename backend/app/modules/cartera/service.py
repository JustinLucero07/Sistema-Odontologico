"""Cartera de la consulta: todo lo que se debe, lo cobrado y lo que viene.

Mismas reglas que el estado de cuenta de cada paciente (payments.service):
el saldo es lo cargado menos lo pagado, ambos sin anulados, y un cargo está
pagado por los cobros aplicados a él. Aquí solo se suman de todos a la vez.
"""

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.credits.models import Credit
from app.modules.expenses.constants import EXPENSE_CATEGORIES
from app.modules.expenses.models import RecurringExpense
from app.modules.patients.models import Patient
from app.modules.payments.constants import PAYMENT_METHODS, money
from app.modules.payments.models import Charge, Installment, Payment
from app.modules.professionals.models import Professional
from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
from app.modules.treatments.models import Treatment

ZERO = Decimal("0.00")
CAT = dict(EXPENSE_CATEGORIES)
MET = {c: l for c, l, _ in PAYMENT_METHODS}


async def portfolio(db: AsyncSession, clinic_id: uuid.UUID) -> dict:
    today = date.today()
    patients = {
        p.id: p
        for p in (await db.execute(select(Patient).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)))).scalars()
    }
    name = lambda pid: f"{patients[pid].first_name} {patients[pid].last_name}" if pid in patients else "Paciente dado de baja"

    charges = list(
        (await db.execute(select(Charge).where(Charge.clinic_id == clinic_id, Charge.voided_at.is_(None)))).scalars()
    )
    payments = list(
        (await db.execute(select(Payment).where(Payment.clinic_id == clinic_id, Payment.voided_at.is_(None)))).scalars()
    )
    in_credit = set((await db.execute(select(Credit.charge_id).where(Credit.clinic_id == clinic_id, Credit.voided_at.is_(None)))).scalars())

    paid_by_charge: dict = defaultdict(lambda: ZERO)
    paid_by_patient: dict = defaultdict(lambda: ZERO)
    last_payment: dict = {}
    for p in payments:
        paid_by_patient[p.patient_id] += p.amount
        if p.charge_id:
            paid_by_charge[p.charge_id] += p.amount
        if p.patient_id not in last_payment or p.received_on > last_payment[p.patient_id]:
            last_payment[p.patient_id] = p.received_on

    charge_rows = []
    charged_by_patient: dict = defaultdict(lambda: ZERO)
    open_by_patient: dict = defaultdict(int)
    oldest: dict = {}
    for c in charges:
        charged_by_patient[c.patient_id] += c.amount
        paid = money(min(paid_by_charge.get(c.id, ZERO), c.amount))
        pending = money(c.amount - paid)
        status = "pagada" if pending <= ZERO else ("parcial" if paid > ZERO else "pendiente")
        if pending > ZERO:
            open_by_patient[c.patient_id] += 1
            if c.patient_id not in oldest or c.issued_on < oldest[c.patient_id]:
                oldest[c.patient_id] = c.issued_on
        charge_rows.append({
            "charge_id": c.id, "patient_id": c.patient_id, "patient_name": name(c.patient_id),
            "description": c.description, "issued_on": c.issued_on, "amount": money(c.amount), "paid": paid,
            "pending": pending, "status": status, "in_credit": c.id in in_credit,
            "days_open": (today - c.issued_on).days if pending > ZERO else 0,
        })
    charge_rows.sort(key=lambda r: (r["status"] == "pagada", -r["pending"], r["issued_on"]))

    credit_patients = {c.patient_id for c in charges if c.id in in_credit}
    patient_rows = []
    for pid in set(charged_by_patient) | set(paid_by_patient):
        if pid not in patients:
            continue
        balance = money(charged_by_patient[pid] - paid_by_patient[pid])
        status = "debe" if balance > ZERO else ("a_favor" if balance < ZERO else "saldado")
        p = patients[pid]
        patient_rows.append({
            "patient_id": pid, "patient_name": name(pid), "national_id": p.national_id, "phone": p.whatsapp or p.phone,
            "total_charged": money(charged_by_patient[pid]), "total_paid": money(paid_by_patient[pid]), "balance": balance,
            "status": status, "open_charges": open_by_patient[pid], "oldest_pending_on": oldest.get(pid),
            "days_pending": (today - oldest[pid]).days if pid in oldest and balance > ZERO else None,
            "last_payment_on": last_payment.get(pid), "in_credit": pid in credit_patients,
        })
    patient_rows.sort(key=lambda r: (-r["balance"], r["patient_name"]))

    items = (
        await db.execute(
            select(TreatmentPlanItem, TreatmentPlan, Treatment, Professional)
            .join(TreatmentPlan, TreatmentPlan.id == TreatmentPlanItem.plan_id)
            .join(Treatment, Treatment.id == TreatmentPlanItem.treatment_id)
            .outerjoin(Professional, Professional.id == TreatmentPlanItem.professional_id)
            .where(TreatmentPlan.clinic_id == clinic_id)
        )
    ).all()
    treat_rows = []
    for it, plan, tr, prof in items:
        if plan.patient_id not in patients:
            continue
        net = money(Decimal(it.price or 0) - Decimal(it.discount or 0))
        treat_rows.append({
            "item_id": it.id, "patient_id": plan.patient_id, "patient_name": name(plan.patient_id), "plan_title": plan.title,
            "treatment": tr.name, "fdi_number": it.fdi_number, "status": it.status, "net_price": net,
            "professional_name": f"{prof.first_name} {prof.last_name}" if prof else None,
            "estimated_date": it.estimated_date, "completed_date": it.completed_date,
        })
    orden = {"en_progreso": 0, "aprobado": 1, "propuesto": 2, "completado": 3, "rechazado": 4, "cancelado": 5}
    treat_rows.sort(key=lambda r: (orden.get(r["status"], 9), r["patient_name"]))

    total_charged = money(sum(charged_by_patient.values(), ZERO))
    total_paid = money(sum(paid_by_patient.values(), ZERO))
    en_curso = [t for t in treat_rows if t["status"] == "en_progreso"]
    planeados = [t for t in treat_rows if t["status"] in ("aprobado", "propuesto")]
    return {
        "summary": {
            "total_charged": total_charged, "total_paid": total_paid,
            "receivable": money(sum((r["balance"] for r in patient_rows if r["balance"] > 0), ZERO)),
            "credit_balance": money(-sum((r["balance"] for r in patient_rows if r["balance"] < 0), ZERO)),
            "patients_owing": sum(r["status"] == "debe" for r in patient_rows),
            "patients_settled": sum(r["status"] == "saldado" for r in patient_rows),
            "patients_credit": sum(r["status"] == "a_favor" for r in patient_rows),
            "open_charges": sum(r["status"] != "pagada" for r in charge_rows),
            "treatments_in_progress": len(en_curso),
            "treatments_in_progress_value": money(sum((t["net_price"] for t in en_curso), ZERO)),
            "treatments_planned": len(planeados),
            "treatments_planned_value": money(sum((t["net_price"] for t in planeados), ZERO)),
            "collection_rate": float(total_paid / total_charged) if total_charged > 0 else None,
        },
        "patients": patient_rows, "charges": charge_rows, "treatments": treat_rows,
    }


# ---- Gastos fijos ---------------------------------------------------------

def _due_on(r: RecurringExpense, today: date) -> date:
    return today.replace(day=r.day_of_month)


def _rec_out(r: RecurringExpense, today: date) -> dict:
    mes = today.strftime("%Y-%m")
    return {
        "id": r.id, "description": r.description, "category": r.category, "category_label": CAT.get(r.category, r.category),
        "amount": money(r.amount), "method": r.method, "method_label": MET.get(r.method, r.method),
        "day_of_month": r.day_of_month, "supplier_name": r.supplier_name, "is_active": r.is_active,
        "last_registered_month": r.last_registered_month,
        "due_this_month": r.is_active and r.last_registered_month != mes, "due_on": _due_on(r, today),
    }


async def list_recurring(db: AsyncSession, clinic_id: uuid.UUID) -> list[dict]:
    today = date.today()
    rows = (await db.execute(
        select(RecurringExpense).where(RecurringExpense.clinic_id == clinic_id).order_by(RecurringExpense.day_of_month)
    )).scalars()
    return [_rec_out(r, today) for r in rows]


async def _rec_or_404(db, clinic_id, rid) -> RecurringExpense:
    r = await db.get(RecurringExpense, rid)
    if r is None or r.clinic_id != clinic_id:
        raise HTTPException(404, "Gasto fijo no encontrado")
    return r


async def save_recurring(db, clinic_id, actor_id, payload, rid=None) -> dict:
    if rid is None:
        r = RecurringExpense(clinic_id=clinic_id, created_at=datetime.now(timezone.utc), **payload.model_dump())
        db.add(r)
    else:
        r = await _rec_or_404(db, clinic_id, rid)
        for k, v in payload.model_dump().items():
            setattr(r, k, v)
    await db.flush()
    await record_audit(db, clinic_id=clinic_id, user_id=actor_id, action="update" if rid else "create",
                       entity_type="recurring_expense", entity_id=str(r.id), after={"amount": str(r.amount)})
    return _rec_out(r, date.today())


async def delete_recurring(db, clinic_id, actor_id, rid) -> None:
    # Es una plantilla: borrarla no toca ningún egreso ya registrado.
    r = await _rec_or_404(db, clinic_id, rid)
    await record_audit(db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="recurring_expense",
                       entity_id=str(r.id), before={"description": r.description})
    await db.delete(r)


async def register_recurring(db, clinic_id, actor_id, rid, payload) -> dict:
    """Registra el gasto fijo como egreso real del mes."""
    from app.modules.expenses.schemas import ExpenseCreate
    from app.modules.expenses.service import create_expense

    r = await _rec_or_404(db, clinic_id, rid)
    today = date.today()
    mes = today.strftime("%Y-%m")
    if r.last_registered_month == mes:
        raise HTTPException(409, "Este gasto fijo ya se registró este mes")
    out = await create_expense(db, clinic_id, actor_id, ExpenseCreate(
        spent_on=payload.spent_on or today, category=r.category, description=r.description,
        amount=payload.amount or r.amount, method=r.method, supplier_name=r.supplier_name,
        notes="Gasto fijo mensual",
    ))
    r.last_registered_month = mes
    return out


# ---- Proyección de flujo --------------------------------------------------

async def projection(db: AsyncSession, clinic_id: uuid.UUID, days: int) -> dict:
    from app.modules.credits.service import get_credit

    today = date.today()
    hasta = today + timedelta(days=days)
    names = {
        p.id: f"{p.first_name} {p.last_name}"
        for p in (await db.execute(select(Patient).where(Patient.clinic_id == clinic_id))).scalars()
    }
    items, overdue = [], ZERO

    credits = (await db.execute(select(Credit.id).where(Credit.clinic_id == clinic_id, Credit.voided_at.is_(None)))).scalars().all()
    for cid in credits:
        det = await get_credit(db, clinic_id, cid)
        for q in det.installments:
            if q.pending <= 0:
                continue
            if q.due_on < today:
                overdue += q.pending
            elif q.due_on <= hasta:
                items.append({"on": q.due_on, "kind": "cuota_credito", "label": f"Cuota {q.number} · {det.charge_description}",
                              "patient_name": det.patient_name, "amount": money(q.pending)})

    # Planes de cuotas simples sobre un cargo (fuera de créditos).
    cuotas = (await db.execute(
        select(Installment, Charge).join(Charge, Charge.id == Installment.charge_id)
        .where(Charge.clinic_id == clinic_id, Charge.voided_at.is_(None))
    )).all()
    pagos = defaultdict(lambda: ZERO)
    for cid, amt in (await db.execute(select(Payment.charge_id, Payment.amount).where(
        Payment.clinic_id == clinic_id, Payment.voided_at.is_(None), Payment.charge_id.is_not(None)))).all():
        pagos[cid] += amt
    por_cargo = defaultdict(list)
    for ins, ch in cuotas:
        por_cargo[ch.id].append((ins, ch))
    for cid, filas in por_cargo.items():
        resto = pagos[cid]
        for ins, ch in sorted(filas, key=lambda f: f[0].number):
            cubre = min(resto, ins.amount); resto -= cubre
            pend = money(ins.amount - cubre)
            if pend <= 0:
                continue
            if ins.due_on < today:
                overdue += pend
            elif ins.due_on <= hasta:
                items.append({"on": ins.due_on, "kind": "cuota_cargo", "label": f"Cuota {ins.number} · {ch.description}",
                              "patient_name": names.get(ch.patient_id), "amount": pend})

    for r in await list_recurring(db, clinic_id):
        if not r["is_active"]:
            continue
        # Este mes si aún no se pagó; los meses siguientes dentro del rango.
        d = r["due_on"]
        mes = d
        while mes <= hasta:
            pendiente = not (mes.year == today.year and mes.month == today.month and not r["due_this_month"])
            if pendiente and mes >= today - timedelta(days=31):
                items.append({"on": max(mes, today), "kind": "gasto_fijo", "label": r["description"],
                              "patient_name": None, "amount": -r["amount"]})
            mes = (mes.replace(day=1) + timedelta(days=32)).replace(day=r["day_of_month"])

    items.sort(key=lambda i: i["on"])
    ent = money(sum((i["amount"] for i in items if i["amount"] > 0), ZERO))
    sal = money(-sum((i["amount"] for i in items if i["amount"] < 0), ZERO))
    return {"days": days, "expected_in": ent, "expected_out": sal, "net": money(ent - sal), "overdue_in": money(overdue), "items": items}
