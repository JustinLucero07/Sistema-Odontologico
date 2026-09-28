import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.patients.service import get_patient_or_404
from app.modules.payments.constants import (
    CASH_METHOD,
    PAYMENT_METHODS,
    money,
)
from app.modules.payments.models import CashSession, Charge, Installment, Payment
from app.modules.payments.schemas import (
    AccountStatement,
    CashSessionOut,
    CashSessionClose,
    CashSessionOpen,
    ChargeCreate,
    ChargeOut,
    DailyCashReport,
    InstallmentPlanCreate,
    InstallmentStatus,
    MethodBreakdown,
    PaymentCreate,
)

ZERO = Decimal("0.00")
_METHOD_LABELS = {code: label for code, label, _ in PAYMENT_METHODS}


# ---- Reading ------------------------------------------------------------


async def _charges_for(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Charge]:
    result = await db.execute(
        select(Charge)
        .options(selectinload(Charge.installments), selectinload(Charge.payments))
        .where(Charge.clinic_id == clinic_id, Charge.patient_id == patient_id)
        .order_by(Charge.issued_on.desc(), Charge.created_at.desc())
    )
    return list(result.scalars().all())


async def _payments_for(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Payment]:
    result = await db.execute(
        select(Payment)
        .where(Payment.clinic_id == clinic_id, Payment.patient_id == patient_id)
        .order_by(Payment.received_on.desc(), Payment.created_at.desc())
    )
    return list(result.scalars().all())


def _paid_on(charge: Charge) -> Decimal:
    """Only payments that still stand count. A voided payment leaves its row
    for the audit trail but must not keep a charge looking settled."""
    return money(sum((p.amount for p in charge.payments if p.voided_at is None), ZERO))


def _installment_statuses(charge: Charge, paid: Decimal, today: date) -> list[InstallmentStatus]:
    """Coverage is walked oldest-first: money received settles the earliest
    instalment still open, which is how a clinic reads a payment plan."""
    remaining = paid
    rows: list[InstallmentStatus] = []
    for item in sorted(charge.installments, key=lambda i: i.number):
        covered = min(remaining, item.amount)
        remaining = money(remaining - covered)
        pending = money(item.amount - covered)
        if pending <= ZERO:
            state = "pagada"
        elif item.due_on < today:
            state = "vencida"
        elif covered > ZERO:
            state = "parcial"
        else:
            state = "pendiente"
        rows.append(
            InstallmentStatus(
                number=item.number,
                due_on=item.due_on,
                amount=money(item.amount),
                paid=money(covered),
                pending=pending,
                status=state,
            )
        )
    return rows


def _to_charge_out(charge: Charge, today: date) -> ChargeOut:
    amount = money(charge.amount)
    paid = _paid_on(charge)
    pending = money(amount - paid)
    if charge.voided_at is not None:
        state = "anulada"
    elif pending <= ZERO:
        state = "pagada"
    elif paid > ZERO:
        state = "parcial"
    else:
        state = "pendiente"
    return ChargeOut(
        id=charge.id,
        patient_id=charge.patient_id,
        budget_id=charge.budget_id,
        description=charge.description,
        amount=amount,
        issued_on=charge.issued_on,
        created_at=charge.created_at,
        notes=charge.notes,
        voided_at=charge.voided_at,
        void_reason=charge.void_reason,
        paid=paid,
        pending=pending if charge.voided_at is None else ZERO,
        status=state,
        installments=_installment_statuses(charge, paid, today),
    )


async def get_statement(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> AccountStatement:
    """The balance is DERIVED on every read, never stored. A stored balance is
    a second source of truth that drifts the first time a void is recorded."""
    await get_patient_or_404(db, clinic_id, patient_id)
    today = date.today()

    charges = await _charges_for(db, clinic_id, patient_id)
    payments = await _payments_for(db, clinic_id, patient_id)

    live_charges = [c for c in charges if c.voided_at is None]
    live_payments = [p for p in payments if p.voided_at is None]

    total_charged = money(sum((c.amount for c in live_charges), ZERO))
    total_paid = money(sum((p.amount for p in live_payments), ZERO))
    unallocated = money(sum((p.amount for p in live_payments if p.charge_id is None), ZERO))

    charge_outs = [_to_charge_out(c, today) for c in charges]
    overdue = money(
        sum(
            (
                row.pending
                for out in charge_outs
                if out.status not in ("anulada", "pagada")
                for row in out.installments
                if row.status == "vencida"
            ),
            ZERO,
        )
    )

    return AccountStatement(
        patient_id=patient_id,
        total_charged=total_charged,
        total_paid=total_paid,
        balance=money(total_charged - total_paid),
        unallocated=unallocated,
        overdue_amount=overdue,
        charges=charge_outs,
        payments=payments,
    )


async def get_charge_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, charge_id: uuid.UUID
) -> Charge:
    result = await db.execute(
        select(Charge)
        .options(selectinload(Charge.installments), selectinload(Charge.payments))
        .where(Charge.id == charge_id, Charge.clinic_id == clinic_id)
    )
    charge = result.scalar_one_or_none()
    if charge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado")
    return charge


# ---- Charges ------------------------------------------------------------


async def create_charge(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: ChargeCreate,
) -> Charge:
    await get_patient_or_404(db, clinic_id, patient_id)
    charge = Charge(
        clinic_id=clinic_id,
        patient_id=patient_id,
        description=payload.description,
        amount=money(payload.amount),
        issued_on=payload.issued_on or date.today(),
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        notes=payload.notes,
    )
    db.add(charge)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="charge",
        entity_id=str(charge.id),
        after={"patient_id": str(patient_id), "amount": str(charge.amount), "description": charge.description},
    )
    await db.refresh(charge, ["installments", "payments"])
    return charge


async def charge_for_accepted_budget(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, budget
) -> Charge | None:
    """Raised when a budget is accepted, capturing the agreed total.

    Idempotent: a budget that already has a charge returns it untouched, so a
    repeated acceptance cannot bill the patient twice. The database backs this
    with a unique constraint rather than trusting this check alone."""
    existing = await db.execute(
        select(Charge).where(Charge.clinic_id == clinic_id, Charge.budget_id == budget.id)
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found

    total = money(budget.total)
    if total <= ZERO:
        return None

    charge = Charge(
        clinic_id=clinic_id,
        patient_id=budget.patient_id,
        budget_id=budget.id,
        description=f"Presupuesto aceptado · {len(budget.items)} tratamiento(s)",
        amount=total,
        issued_on=date.today(),
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(charge)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="charge",
        entity_id=str(charge.id),
        after={"budget_id": str(budget.id), "amount": str(total), "origin": "budget_accepted"},
    )
    return charge


async def void_charge(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, charge_id: uuid.UUID, reason: str
) -> Charge:
    charge = await get_charge_or_404(db, clinic_id, charge_id)
    if charge.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cargo ya está anulado")

    # Voiding a charge that money was received against would leave those
    # payments pointing at nothing. The payments have to be dealt with first,
    # deliberately, one at a time.
    live = [p for p in charge.payments if p.voided_at is None]
    if live:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El cargo tiene {len(live)} pago(s) vigente(s). "
                "Anule primero los pagos si corresponde."
            ),
        )

    charge.voided_at = datetime.now(timezone.utc)
    charge.voided_by_id = actor_id
    charge.void_reason = reason.strip()
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="void", entity_type="charge",
        entity_id=str(charge_id), after={"reason": charge.void_reason},
    )
    return charge


async def _financed_by(db: AsyncSession, charge_id: uuid.UUID) -> bool:
    from app.modules.credits.models import Credit

    found = await db.scalar(
        select(Credit.id).where(
            Credit.voided_at.is_(None),
            (Credit.charge_id == charge_id) | (Credit.interest_charge_id == charge_id),
        ).limit(1)
    )
    return found is not None


async def set_installment_plan(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    charge_id: uuid.UUID,
    payload: InstallmentPlanCreate,
) -> Charge:
    charge = await get_charge_or_404(db, clinic_id, charge_id)
    if charge.voided_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No se puede refinanciar un cargo anulado"
        )
    if await _financed_by(db, charge.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este cargo ya tiene un crédito: refinancie desde el crédito.",
        )

    total = money(charge.amount)
    base = money(total / payload.count)
    amounts = [base] * payload.count
    # The rounding remainder lands on the LAST instalment, so the schedule
    # always sums to the charge exactly — a plan that adds up to a cent less
    # than the debt leaves a balance nobody can pay off.
    amounts[-1] = money(total - base * (payload.count - 1))

    charge.installments.clear()
    await db.flush()
    from datetime import timedelta

    for index, amount in enumerate(amounts):
        charge.installments.append(
            Installment(
                clinic_id=clinic_id,
                number=index + 1,
                due_on=payload.first_due_on + timedelta(days=payload.every_days * index),
                amount=amount,
            )
        )
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="charge",
        entity_id=str(charge_id),
        after={"installments": payload.count, "first_due_on": str(payload.first_due_on)},
    )
    return charge


# ---- Payments -----------------------------------------------------------


async def create_payment(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: PaymentCreate,
) -> Payment:
    await get_patient_or_404(db, clinic_id, patient_id)
    amount = money(payload.amount)

    charge = None
    if payload.charge_id is not None:
        charge = await get_charge_or_404(db, clinic_id, payload.charge_id)
        if charge.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El cargo no pertenece a este paciente",
            )
        if charge.voided_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="El cargo está anulado"
            )
        if await _financed_by(db, charge.id):
            # Pagado por fuera, el crédito no se enteraría y seguiría mostrando
            # cuotas pendientes de algo ya cobrado.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este cargo está financiado con un crédito: registre el pago como cuota del crédito.",
            )
        pending = money(charge.amount - _paid_on(charge))
        # Refusing the overpayment rather than absorbing it keeps the charge's
        # own arithmetic honest; genuine extra money is taken on account.
        if amount > pending:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"El pago ({amount}) supera el saldo pendiente del cargo ({pending}). "
                    "Registre el excedente como pago a cuenta."
                ),
            )

    session = await get_open_session(db, clinic_id) if payload.method == CASH_METHOD else None

    payment = Payment(
        clinic_id=clinic_id,
        patient_id=patient_id,
        charge_id=charge.id if charge else None,
        cash_session_id=session.id if session else None,
        amount=amount,
        method=payload.method,
        reference=payload.reference,
        received_on=payload.received_on or date.today(),
        received_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        notes=payload.notes,
    )
    db.add(payment)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="payment",
        entity_id=str(payment.id),
        after={
            "patient_id": str(patient_id),
            "amount": str(amount),
            "method": payload.method,
            "charge_id": str(charge.id) if charge else None,
        },
    )
    return payment


async def void_payment(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payment_id: uuid.UUID, reason: str
) -> Payment:
    """Money is never deleted. A mistaken payment is reversed in place, with a
    reason, so the day's till still reconciles against what really happened."""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.clinic_id == clinic_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    if payment.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago ya está anulado")

    now = datetime.now(timezone.utc)
    group = [payment]
    if payment.split_group_id is not None:
        # Las dos partes de una cuota (interés y capital) se anulan juntas.
        siblings = (
            await db.execute(
                select(Payment).where(
                    Payment.split_group_id == payment.split_group_id,
                    Payment.id != payment.id,
                    Payment.voided_at.is_(None),
                )
            )
        ).scalars().all()
        group.extend(siblings)
    for item in group:
        item.voided_at = now
        item.voided_by_id = actor_id
        item.void_reason = reason.strip()
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="void", entity_type="payment",
        entity_id=str(payment_id),
        after={"reason": payment.void_reason, "amount": str(payment.amount)},
    )
    return payment


# ---- Cash sessions ------------------------------------------------------


async def get_open_session(db: AsyncSession, clinic_id: uuid.UUID) -> CashSession | None:
    result = await db.execute(
        select(CashSession)
        .where(CashSession.clinic_id == clinic_id, CashSession.closed_at.is_(None))
        .order_by(CashSession.opened_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def open_session(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: CashSessionOpen
) -> CashSession:
    if await get_open_session(db, clinic_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una caja abierta. Ciérrela antes de abrir otra.",
        )
    session = CashSession(
        clinic_id=clinic_id,
        opened_at=datetime.now(timezone.utc),
        opened_by_id=actor_id,
        opening_float=money(payload.opening_float),
    )
    db.add(session)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="open", entity_type="cash_session",
        entity_id=str(session.id), after={"opening_float": str(session.opening_float)},
    )
    return session


async def close_session(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: CashSessionClose
) -> CashSession:
    session = await get_open_session(db, clinic_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay ninguna caja abierta")

    result = await db.execute(
        select(Payment).where(
            Payment.clinic_id == clinic_id,
            Payment.cash_session_id == session.id,
            Payment.voided_at.is_(None),
        )
    )
    taken = money(sum((p.amount for p in result.scalars().all()), ZERO))
    # Los gastos pagados en efectivo con esta caja salieron del cajón.
    from app.modules.expenses.service import cash_expenses_total

    spent = await cash_expenses_total(db, clinic_id, session.id)

    session.expected_cash = money(session.opening_float + taken - spent)
    session.counted_cash = money(payload.counted_cash)
    session.difference = money(session.counted_cash - session.expected_cash)
    session.closed_at = datetime.now(timezone.utc)
    session.closed_by_id = actor_id
    session.notes = payload.notes
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="close", entity_type="cash_session",
        entity_id=str(session.id),
        after={
            "expected": str(session.expected_cash),
            "counted": str(session.counted_cash),
            "difference": str(session.difference),
        },
    )
    return session


async def daily_report(db: AsyncSession, clinic_id: uuid.UUID, day: date) -> DailyCashReport:
    result = await db.execute(
        select(Payment).where(Payment.clinic_id == clinic_id, Payment.received_on == day)
    )
    payments = list(result.scalars().all())
    live = [p for p in payments if p.voided_at is None]
    voided = [p for p in payments if p.voided_at is not None]

    by_method: dict[str, list[Payment]] = {}
    for payment in live:
        by_method.setdefault(payment.method, []).append(payment)

    from app.modules.expenses.models import Expense

    expenses = (
        await db.execute(
            select(Expense).where(
                Expense.clinic_id == clinic_id, Expense.spent_on == day, Expense.voided_at.is_(None)
            )
        )
    ).scalars().all()

    return DailyCashReport(
        day=day,
        expenses_total=money(sum((e.amount for e in expenses), ZERO)),
        expenses_count=len(expenses),
        cash_expenses=money(sum((e.amount for e in expenses if e.method == CASH_METHOD), ZERO)),
        total=money(sum((p.amount for p in live), ZERO)),
        payment_count=len(live),
        by_method=sorted(
            (
                MethodBreakdown(
                    method=code,
                    label=_METHOD_LABELS.get(code, code),
                    total=money(sum((p.amount for p in items), ZERO)),
                    count=len(items),
                )
                for code, items in by_method.items()
            ),
            key=lambda b: b.total,
            reverse=True,
        ),
        voided_total=money(sum((p.amount for p in voided), ZERO)),
        voided_count=len(voided),
    )


async def session_with_totals(db: AsyncSession, clinic_id: uuid.UUID) -> dict | None:
    """La caja abierta con lo que lleva: efectivo cobrado, efectivo gastado y
    lo que debería haber en el cajón en este momento."""
    session = await get_open_session(db, clinic_id)
    if session is None:
        return None
    from app.modules.expenses.service import cash_expenses_total

    cash_in = money(
        sum(
            (
                await db.execute(
                    select(Payment.amount).where(
                        Payment.clinic_id == clinic_id,
                        Payment.cash_session_id == session.id,
                        Payment.voided_at.is_(None),
                    )
                )
            ).scalars().all(),
            ZERO,
        )
    )
    cash_out = await cash_expenses_total(db, clinic_id, session.id)
    out = CashSessionOut.model_validate(session).model_dump()
    out.update(cash_in=cash_in, cash_out=cash_out, expected_now=money(session.opening_float + cash_in - cash_out))
    return out
