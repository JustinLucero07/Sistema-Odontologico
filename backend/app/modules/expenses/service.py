import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.expenses.constants import EXPENSE_CATEGORIES
from app.modules.expenses.models import Expense
from app.modules.expenses.schemas import (
    Breakdown,
    CashSessionRow,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    FinanceSummary,
    MonthRow,
    PaymentRow,
)
from app.modules.patients.models import Patient
from app.modules.payments.constants import CASH_METHOD, PAYMENT_METHODS, money
from app.modules.payments.models import CashSession, Charge, Payment
from app.modules.users.models import User
from app.shared.voiding import apply_void

ZERO = Decimal("0.00")
CATEGORY_LABELS = dict(EXPENSE_CATEGORIES)
METHOD_LABELS = {code: label for code, label, _ in PAYMENT_METHODS}


async def _user_names(db: AsyncSession, ids: set) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = (await db.execute(select(User.id, User.first_name, User.last_name).where(User.id.in_(ids)))).all()
    return {r.id: f"{r.first_name} {r.last_name}" for r in rows}


def _to_out(expense: Expense, names: dict) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id,
        spent_on=expense.spent_on,
        category=expense.category,
        category_label=CATEGORY_LABELS.get(expense.category, expense.category),
        description=expense.description,
        amount=money(expense.amount),
        method=expense.method,
        method_label=METHOD_LABELS.get(expense.method, expense.method),
        supplier_id=expense.supplier_id,
        supplier_name=expense.supplier_name,
        receipt_number=expense.receipt_number,
        cash_session_id=expense.cash_session_id,
        notes=expense.notes,
        created_by_name=names.get(expense.created_by_id),
        created_at=expense.created_at,
        voided_at=expense.voided_at,
        void_reason=expense.void_reason,
    )


async def _get_or_404(db: AsyncSession, clinic_id: uuid.UUID, expense_id: uuid.UUID) -> Expense:
    expense = (
        await db.execute(select(Expense).where(Expense.id == expense_id, Expense.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Egreso no encontrado")
    return expense


async def _supplier_name(db: AsyncSession, clinic_id: uuid.UUID, supplier_id: uuid.UUID | None) -> str | None:
    if supplier_id is None:
        return None
    from app.modules.inventory.models import Supplier

    supplier = (
        await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return supplier.name


async def list_expenses(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date, category: str | None = None
) -> list[ExpenseOut]:
    query = select(Expense).where(
        Expense.clinic_id == clinic_id, Expense.spent_on >= date_from, Expense.spent_on <= date_to
    )
    if category:
        query = query.where(Expense.category == category)
    rows = (await db.execute(query.order_by(Expense.spent_on.desc(), Expense.created_at.desc()))).scalars().all()
    names = await _user_names(db, {r.created_by_id for r in rows})
    return [_to_out(r, names) for r in rows]


async def create_expense(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: ExpenseCreate
) -> ExpenseOut:
    from app.modules.payments.service import get_open_session

    supplier_name = payload.supplier_name or await _supplier_name(db, clinic_id, payload.supplier_id)
    session = None
    # Un gasto en efectivo de hoy sale de la caja abierta: el arqueo lo
    # descontará. Si es de otro día, o no hay caja abierta, no se asigna.
    if payload.method == CASH_METHOD and payload.spent_on == date.today():
        session = await get_open_session(db, clinic_id)
    expense = Expense(
        clinic_id=clinic_id,
        spent_on=payload.spent_on,
        category=payload.category,
        description=payload.description.strip(),
        amount=payload.amount,
        method=payload.method,
        supplier_id=payload.supplier_id,
        supplier_name=supplier_name,
        receipt_number=(payload.receipt_number or "").strip() or None,
        cash_session_id=session.id if session else None,
        notes=payload.notes,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(expense)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="expense",
        entity_id=str(expense.id),
        after={"amount": str(expense.amount), "category": expense.category, "method": expense.method},
    )
    return _to_out(expense, await _user_names(db, {actor_id}))


async def update_expense(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, expense_id: uuid.UUID, payload: ExpenseUpdate
) -> ExpenseOut:
    expense = await _get_or_404(db, clinic_id, expense_id)
    if expense.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El egreso está anulado")
    before = {"description": expense.description, "category": expense.category, "spent_on": expense.spent_on}
    expense.spent_on = payload.spent_on
    expense.category = payload.category
    expense.description = payload.description.strip()
    expense.supplier_id = payload.supplier_id
    expense.supplier_name = payload.supplier_name or await _supplier_name(db, clinic_id, payload.supplier_id)
    expense.receipt_number = (payload.receipt_number or "").strip() or None
    expense.notes = payload.notes
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="expense",
        entity_id=str(expense_id), before=before, after=payload.model_dump(mode="json"),
    )
    return _to_out(expense, await _user_names(db, {expense.created_by_id}))


async def void_expense(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, expense_id: uuid.UUID, reason: str
) -> ExpenseOut:
    expense = await _get_or_404(db, clinic_id, expense_id)
    apply_void(expense, actor_id, reason, "El egreso")
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="void", entity_type="expense",
        entity_id=str(expense_id), after={"reason": expense.void_reason, "amount": str(expense.amount)},
    )
    return _to_out(expense, await _user_names(db, {expense.created_by_id}))


async def cash_expenses_total(db: AsyncSession, clinic_id: uuid.UUID, session_id: uuid.UUID) -> Decimal:
    rows = (
        await db.execute(
            select(Expense.amount).where(
                Expense.clinic_id == clinic_id,
                Expense.cash_session_id == session_id,
                Expense.voided_at.is_(None),
            )
        )
    ).scalars().all()
    return money(sum(rows, ZERO))


# ---- Listados y resumen ----------------------------------------------------


async def list_payments(
    db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date, method: str | None = None
) -> list[PaymentRow]:
    query = (
        select(Payment, Patient.first_name, Patient.last_name, Charge.description)
        .join(Patient, Patient.id == Payment.patient_id)
        .outerjoin(Charge, Charge.id == Payment.charge_id)
        .where(Payment.clinic_id == clinic_id, Payment.received_on >= date_from, Payment.received_on <= date_to)
    )
    if method:
        query = query.where(Payment.method == method)
    rows = (await db.execute(query.order_by(Payment.received_on.desc(), Payment.created_at.desc()))).all()
    names = await _user_names(db, {r[0].received_by_id for r in rows})
    return [
        PaymentRow(
            id=p.id,
            received_on=p.received_on,
            patient_id=p.patient_id,
            patient_name=f"{first} {last}",
            concept=concept,
            amount=money(p.amount),
            method=p.method,
            method_label=METHOD_LABELS.get(p.method, p.method),
            reference=p.reference,
            received_by_name=names.get(p.received_by_id),
            voided_at=p.voided_at,
            void_reason=p.void_reason,
        )
        for p, first, last, concept in rows
    ]


def _months(date_from: date, date_to: date) -> list[str]:
    months, y, m = [], date_from.year, date_from.month
    while (y, m) <= (date_to.year, date_to.month):
        months.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


async def summary(db: AsyncSession, clinic_id: uuid.UUID, date_from: date, date_to: date) -> FinanceSummary:
    payments = (
        await db.execute(
            select(Payment).where(
                Payment.clinic_id == clinic_id,
                Payment.voided_at.is_(None),
                Payment.received_on >= date_from,
                Payment.received_on <= date_to,
            )
        )
    ).scalars().all()
    expenses = (
        await db.execute(
            select(Expense).where(
                Expense.clinic_id == clinic_id,
                Expense.voided_at.is_(None),
                Expense.spent_on >= date_from,
                Expense.spent_on <= date_to,
            )
        )
    ).scalars().all()
    sales_rows = (
        await db.execute(
            select(Charge.amount).where(
                Charge.clinic_id == clinic_id,
                Charge.voided_at.is_(None),
                Charge.issued_on >= date_from,
                Charge.issued_on <= date_to,
            )
        )
    ).scalars().all()

    from app.modules.reports.service import _receivables

    receivables, _ = await _receivables(db, clinic_id)

    by_method: dict[str, list[Decimal]] = defaultdict(list)
    for p in payments:
        by_method[p.method].append(p.amount)
    by_category: dict[str, list[Decimal]] = defaultdict(list)
    for e in expenses:
        by_category[e.category].append(e.amount)

    monthly_income: dict[str, Decimal] = defaultdict(lambda: ZERO)
    monthly_expenses: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for p in payments:
        monthly_income[p.received_on.strftime("%Y-%m")] += p.amount
    for e in expenses:
        monthly_expenses[e.spent_on.strftime("%Y-%m")] += e.amount

    income = money(sum((p.amount for p in payments), ZERO))
    spent = money(sum((e.amount for e in expenses), ZERO))

    def breakdown(groups: dict, labels: dict) -> list[Breakdown]:
        return sorted(
            (
                Breakdown(code=code, label=labels.get(code, code), total=money(sum(values, ZERO)), count=len(values))
                for code, values in groups.items()
            ),
            key=lambda b: b.total,
            reverse=True,
        )

    return FinanceSummary(
        date_from=date_from,
        date_to=date_to,
        sales=money(sum(sales_rows, ZERO)),
        income=income,
        expenses=spent,
        net=money(income - spent),
        receivables=money(receivables),
        income_by_method=breakdown(by_method, METHOD_LABELS),
        expenses_by_category=breakdown(by_category, CATEGORY_LABELS),
        monthly=[
            MonthRow(
                month=m,
                income=money(monthly_income[m]),
                expenses=money(monthly_expenses[m]),
                net=money(monthly_income[m] - monthly_expenses[m]),
            )
            for m in _months(date_from, date_to)
        ],
    )


async def cash_sessions(db: AsyncSession, clinic_id: uuid.UUID, limit: int = 60) -> list[CashSessionRow]:
    sessions = (
        await db.execute(
            select(CashSession)
            .where(CashSession.clinic_id == clinic_id)
            .order_by(CashSession.opened_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    names = await _user_names(db, {s.opened_by_id for s in sessions} | {s.closed_by_id for s in sessions})
    rows = []
    for s in sessions:
        cash_in = money(
            sum(
                (
                    await db.execute(
                        select(Payment.amount).where(
                            Payment.cash_session_id == s.id, Payment.voided_at.is_(None)
                        )
                    )
                ).scalars().all(),
                ZERO,
            )
        )
        cash_out = await cash_expenses_total(db, clinic_id, s.id)
        rows.append(
            CashSessionRow(
                id=s.id,
                opened_at=s.opened_at,
                closed_at=s.closed_at,
                opened_by_name=names.get(s.opened_by_id),
                closed_by_name=names.get(s.closed_by_id),
                opening_float=money(s.opening_float),
                cash_in=cash_in,
                cash_out=cash_out,
                # Una caja cerrada muestra lo que se calculó al cerrarla (queda
                # guardado); una abierta, lo que va hasta ahora.
                expected_cash=money(s.expected_cash)
                if s.expected_cash is not None
                else money(s.opening_float + cash_in - cash_out),
                counted_cash=s.counted_cash,
                difference=s.difference,
                notes=s.notes,
            )
        )
    return rows
