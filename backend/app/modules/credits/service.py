import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.credits.amortization import schedule
from app.modules.credits.constants import FREQUENCY_DAYS, FREQUENCY_LABELS
from app.modules.credits.models import Credit, CreditInstallment
from app.modules.credits.schemas import (
    CreditCreate,
    CreditDetail,
    CreditOut,
    CreditPayment,
    CreditPaymentRow,
    CreditRestructure,
    CreditSummary,
    CreditUpdate,
    InstallmentRow,
    Preview,
    PreviewRow,
)
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.modules.payments.constants import CASH_METHOD, PAYMENT_METHODS, money
from app.modules.payments.models import Charge, Payment
from app.shared.voiding import apply_void

ZERO = Decimal("0.00")
METHOD_LABELS = {code: label for code, label, _ in PAYMENT_METHODS}


# ---- Cálculo --------------------------------------------------------------


def preview(principal: Decimal, count: int, monthly_rate: Decimal, frequency: str, first_due_on: date) -> Preview:
    rows = schedule(principal, count, monthly_rate, FREQUENCY_DAYS[frequency], first_due_on)
    return Preview(
        rows=[PreviewRow(number=r.number, due_on=r.due_on, principal=r.principal, interest=r.interest, amount=r.amount) for r in rows],
        total=money(sum((r.amount for r in rows), ZERO)),
        total_interest=money(sum((r.interest for r in rows), ZERO)),
        installment_amount=money(rows[0].amount) if rows else ZERO,
        annual_rate=money(Decimal(monthly_rate) * 12),
    )


def _active(credit: Credit) -> list[CreditInstallment]:
    return sorted((i for i in credit.installments if i.superseded_at is None), key=lambda i: i.number)


def _coverage(rows: list[CreditInstallment], paid: Decimal, today: date) -> list[InstallmentRow]:
    """El dinero cobrado cubre las cuotas de la más antigua a la más nueva."""
    remaining = paid
    out = []
    for r in rows:
        covered = min(remaining, r.amount)
        remaining = money(remaining - covered)
        pending = money(r.amount - covered)
        if pending <= ZERO:
            state = "pagada"
        elif r.due_on < today:
            state = "vencida"
        elif covered > ZERO:
            state = "parcial"
        else:
            state = "pendiente"
        out.append(
            InstallmentRow(
                number=r.number, due_on=r.due_on, principal=money(r.principal), interest=money(r.interest),
                amount=money(r.amount), paid=money(covered), pending=pending, status=state,
                days_late=(today - r.due_on).days if state == "vencida" else 0,
            )
        )
    return out


def _interest_covered(rows: list[CreditInstallment], paid: Decimal) -> Decimal:
    """Cuánto de lo pagado corresponde a interés: dentro de cada cuota se
    cubre primero el interés y luego el capital, como en cualquier crédito."""
    remaining = paid
    interest = ZERO
    for r in rows:
        if remaining <= ZERO:
            break
        take = min(remaining, r.interest)
        interest += take
        remaining -= take
        remaining -= min(remaining, r.principal)
    return money(interest)


# ---- Lectura ----------------------------------------------------------------


async def _load(db: AsyncSession, clinic_id: uuid.UUID, credit_id: uuid.UUID) -> Credit:
    credit = (
        await db.execute(
            select(Credit)
            .options(selectinload(Credit.installments))
            .where(Credit.id == credit_id, Credit.clinic_id == clinic_id)
        )
    ).scalar_one_or_none()
    if credit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crédito no encontrado")
    return credit


async def _payments(db: AsyncSession, credit_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Payment]]:
    if not credit_ids:
        return {}
    rows = (
        await db.execute(select(Payment).where(Payment.credit_id.in_(credit_ids)).order_by(Payment.received_on, Payment.created_at))
    ).scalars().all()
    grouped: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for p in rows:
        grouped[p.credit_id].append(p)
    return grouped


async def _allowed(db: AsyncSession, clinic_id: uuid.UUID, patient_ids: set[uuid.UUID]) -> dict[uuid.UUID, bool]:
    from app.modules.privacy.service import communications_revoked

    return {pid: not await communications_revoked(db, clinic_id, pid) for pid in patient_ids}


def _to_out(credit: Credit, patient: Patient, charge: Charge, payments: list[Payment], allowed: bool, today: date) -> CreditOut:
    rows = _active(credit)
    paid = money(sum((p.amount for p in payments if p.voided_at is None), ZERO))
    cov = _coverage(rows, paid, today)
    total = money(sum((r.amount for r in rows), ZERO))
    total_interest = money(sum((r.interest for r in rows), ZERO))
    pending = money(total - paid)
    overdue = money(sum((c.pending for c in cov if c.status == "vencida"), ZERO))
    nxt = next((c for c in cov if c.pending > ZERO), None)
    if credit.voided_at is not None:
        state = "anulado"
    elif pending <= ZERO:
        state = "pagado"
    elif overdue > ZERO:
        state = "vencido"
    else:
        state = "al_dia"
    return CreditOut(
        id=credit.id,
        patient_id=credit.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        patient_phone=patient.whatsapp or patient.phone,
        charge_id=credit.charge_id,
        charge_description=charge.description,
        interest_charge_id=credit.interest_charge_id,
        down_payment=money(credit.down_payment),
        principal=money(credit.principal),
        monthly_rate=credit.monthly_rate,
        frequency=credit.frequency,
        frequency_label=FREQUENCY_LABELS.get(credit.frequency, credit.frequency),
        installment_count=credit.installment_count,
        first_due_on=credit.first_due_on,
        total=total,
        total_interest=total_interest,
        paid=paid,
        pending=pending if credit.voided_at is None else ZERO,
        overdue=overdue if credit.voided_at is None else ZERO,
        days_late=max((c.days_late for c in cov), default=0) if credit.voided_at is None else 0,
        next_due_on=nxt.due_on if nxt and credit.voided_at is None else None,
        next_amount=nxt.pending if nxt and credit.voided_at is None else None,
        status=state,
        guarantor_name=credit.guarantor_name,
        guarantor_id_number=credit.guarantor_id_number,
        guarantor_phone=credit.guarantor_phone,
        notes=credit.notes,
        created_at=credit.created_at,
        voided_at=credit.voided_at,
        void_reason=credit.void_reason,
        communications_allowed=allowed,
    )


async def list_credits(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID | None = None, state: str | None = None
) -> list[CreditOut]:
    query = (
        select(Credit, Patient, Charge)
        .options(selectinload(Credit.installments))
        .join(Patient, Patient.id == Credit.patient_id)
        .join(Charge, Charge.id == Credit.charge_id)
        .where(Credit.clinic_id == clinic_id)
    )
    if patient_id:
        query = query.where(Credit.patient_id == patient_id)
    rows = (await db.execute(query.order_by(Credit.created_at.desc()))).all()
    payments = await _payments(db, [c.id for c, _, _ in rows])
    allowed = await _allowed(db, clinic_id, {c.patient_id for c, _, _ in rows})
    today = date.today()
    out = [_to_out(c, p, ch, payments.get(c.id, []), allowed[c.patient_id], today) for c, p, ch in rows]
    if state:
        out = [o for o in out if o.status == state]
    return out


async def get_credit(db: AsyncSession, clinic_id: uuid.UUID, credit_id: uuid.UUID) -> CreditDetail:
    credit = await _load(db, clinic_id, credit_id)
    patient = await db.get(Patient, credit.patient_id)
    charge = await db.get(Charge, credit.charge_id)
    payments = (await _payments(db, [credit.id])).get(credit.id, [])
    allowed = (await _allowed(db, clinic_id, {credit.patient_id}))[credit.patient_id]
    today = date.today()
    base = _to_out(credit, patient, charge, payments, allowed, today)
    paid = money(sum((p.amount for p in payments if p.voided_at is None), ZERO))

    groups: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for p in payments:
        groups[p.split_group_id or p.id].append(p)
    payment_rows = [
        CreditPaymentRow(
            group_id=gid,
            received_on=items[0].received_on,
            amount=money(sum((i.amount for i in items), ZERO)),
            method=items[0].method,
            method_label=METHOD_LABELS.get(items[0].method, items[0].method),
            reference=items[0].reference,
            voided_at=items[0].voided_at,
            void_reason=items[0].void_reason,
            payment_ids=[i.id for i in items],
        )
        for gid, items in groups.items()
    ]
    payment_rows.sort(key=lambda r: r.received_on, reverse=True)
    return CreditDetail(**base.model_dump(), installments=_coverage(_active(credit), paid, today), payments=payment_rows)


async def summary(db: AsyncSession, clinic_id: uuid.UUID) -> CreditSummary:
    credits = await list_credits(db, clinic_id)
    live = [c for c in credits if c.status in ("al_dia", "vencido")]
    month_start = date.today().replace(day=1)
    rows = (
        await db.execute(
            select(Payment.amount).where(
                Payment.clinic_id == clinic_id,
                Payment.credit_id.is_not(None),
                Payment.voided_at.is_(None),
                Payment.received_on >= month_start,
            )
        )
    ).scalars().all()
    return CreditSummary(
        active_count=len(live),
        overdue_count=sum(1 for c in live if c.status == "vencido"),
        outstanding=money(sum((c.pending for c in live), ZERO)),
        overdue_amount=money(sum((c.overdue for c in live), ZERO)),
        collected_this_month=money(sum(rows, ZERO)),
    )


# ---- Escritura -------------------------------------------------------------


async def create_credit(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: CreditCreate
) -> CreditDetail:
    from app.modules.payments.schemas import ChargeCreate, PaymentCreate
    from app.modules.payments.service import (
        _financed_by,
        _paid_on,
        create_charge,
        create_payment,
        get_charge_or_404,
    )

    await get_patient_or_404(db, clinic_id, patient_id)
    charge = await get_charge_or_404(db, clinic_id, payload.charge_id)
    if charge.patient_id != patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cargo no pertenece a este paciente")
    if charge.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cargo está anulado")
    if await _financed_by(db, charge.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este cargo ya tiene un crédito vigente")

    pending = money(charge.amount - _paid_on(charge))
    if payload.down_payment >= pending:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La entrada ({payload.down_payment}) cubre todo el saldo ({pending}): no hay nada que financiar.",
        )

    if payload.down_payment > ZERO:
        await create_payment(
            db, clinic_id, actor_id, patient_id,
            PaymentCreate(
                amount=payload.down_payment,
                method=payload.down_payment_method,
                charge_id=charge.id,
                reference=payload.down_payment_reference,
                notes="Entrada del crédito",
            ),
        )

    principal = money(pending - payload.down_payment)
    rows = schedule(principal, payload.installment_count, payload.monthly_rate, FREQUENCY_DAYS[payload.frequency], payload.first_due_on)
    total_interest = money(sum((r.interest for r in rows), ZERO))

    interest_charge = None
    if total_interest > ZERO:
        interest_charge = await create_charge(
            db, clinic_id, actor_id, patient_id,
            ChargeCreate(
                description=f"Interés de financiamiento · {charge.description}"[:300],
                amount=total_interest,
                notes=f"{payload.installment_count} cuotas al {payload.monthly_rate}% mensual",
            ),
        )

    # El calendario anterior de cuotas simples (si lo había) queda sustituido.
    charge.installments.clear()

    credit = Credit(
        clinic_id=clinic_id,
        patient_id=patient_id,
        charge_id=charge.id,
        interest_charge_id=interest_charge.id if interest_charge else None,
        down_payment=payload.down_payment,
        principal=principal,
        monthly_rate=payload.monthly_rate,
        frequency=payload.frequency,
        installment_count=payload.installment_count,
        first_due_on=payload.first_due_on,
        guarantor_name=(payload.guarantor_name or "").strip() or None,
        guarantor_id_number=(payload.guarantor_id_number or "").strip() or None,
        guarantor_phone=(payload.guarantor_phone or "").strip() or None,
        notes=payload.notes,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        installments=[
            CreditInstallment(
                clinic_id=clinic_id, number=r.number, due_on=r.due_on,
                principal=r.principal, interest=r.interest, amount=r.amount,
            )
            for r in rows
        ],
    )
    db.add(credit)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="credit",
        entity_id=str(credit.id),
        after={
            "principal": str(principal), "installments": payload.installment_count,
            "monthly_rate": str(payload.monthly_rate), "down_payment": str(payload.down_payment),
        },
    )
    return await get_credit(db, clinic_id, credit.id)


async def update_credit(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, credit_id: uuid.UUID, payload: CreditUpdate
) -> CreditDetail:
    credit = await _load(db, clinic_id, credit_id)
    before = {"guarantor_name": credit.guarantor_name, "notes": credit.notes}
    credit.guarantor_name = (payload.guarantor_name or "").strip() or None
    credit.guarantor_id_number = (payload.guarantor_id_number or "").strip() or None
    credit.guarantor_phone = (payload.guarantor_phone or "").strip() or None
    credit.notes = payload.notes
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="credit",
        entity_id=str(credit_id), before=before, after=payload.model_dump(),
    )
    return await get_credit(db, clinic_id, credit_id)


async def pay(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, credit_id: uuid.UUID, payload: CreditPayment
) -> CreditDetail:
    from app.modules.payments.service import _paid_on, get_charge_or_404, get_open_session

    credit = await _load(db, clinic_id, credit_id)
    if credit.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El crédito está anulado")
    payments = (await _payments(db, [credit.id])).get(credit.id, [])
    live = [p for p in payments if p.voided_at is None]
    paid = money(sum((p.amount for p in live), ZERO))
    rows = _active(credit)
    pending = money(sum((r.amount for r in rows), ZERO) - paid)
    if payload.amount > pending:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El pago ({payload.amount}) supera lo que falta del crédito ({pending}).",
        )

    # Reparto entre interés y capital según el calendario.
    interest_paid = money(sum((p.amount for p in live if p.charge_id == credit.interest_charge_id), ZERO))
    interest_part = ZERO
    if credit.interest_charge_id is not None:
        target = _interest_covered(rows, money(paid + payload.amount))
        interest_part = min(max(money(target - interest_paid), ZERO), payload.amount)
        interest_charge = await get_charge_or_404(db, clinic_id, credit.interest_charge_id)
        interest_part = min(interest_part, money(interest_charge.amount - _paid_on(interest_charge)))
    principal_part = money(payload.amount - interest_part)

    session = await get_open_session(db, clinic_id) if payload.method == CASH_METHOD else None
    group = uuid.uuid4()
    now = datetime.now(timezone.utc)
    for charge_id, amount in ((credit.interest_charge_id, interest_part), (credit.charge_id, principal_part)):
        if amount <= ZERO:
            continue
        db.add(
            Payment(
                clinic_id=clinic_id, patient_id=credit.patient_id, charge_id=charge_id, credit_id=credit.id,
                split_group_id=group, cash_session_id=session.id if session else None, amount=amount,
                method=payload.method, reference=(payload.reference or "").strip() or None,
                received_on=payload.received_on or date.today(), received_by_id=actor_id, created_at=now,
                notes=payload.notes or "Cuota de crédito",
            )
        )
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="credit_payment",
        entity_id=str(credit_id),
        after={"amount": str(payload.amount), "interest": str(interest_part), "principal": str(principal_part)},
    )
    return await get_credit(db, clinic_id, credit_id)


async def restructure(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, credit_id: uuid.UUID, payload: CreditRestructure
) -> CreditDetail:
    """Las cuotas pagadas quedan como están; lo que falta (capital e interés ya
    pactado) se reparte en un calendario nuevo, sin intereses adicionales."""
    credit = await _load(db, clinic_id, credit_id)
    if credit.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El crédito está anulado")
    payments = (await _payments(db, [credit.id])).get(credit.id, [])
    paid = money(sum((p.amount for p in payments if p.voided_at is None), ZERO))
    rows = _active(credit)
    now = datetime.now(timezone.utc)

    keep_number = 0
    remaining = paid
    rest_principal = ZERO
    rest_interest = ZERO
    new_rows: list[CreditInstallment] = []
    for r in rows:
        covered = min(remaining, r.amount)
        remaining = money(remaining - covered)
        if covered >= r.amount:
            keep_number = r.number
            continue
        # Cuota con saldo: se sustituye. La parte ya pagada queda como una
        # cuota pagada de ese monto; el resto pasa al calendario nuevo.
        r.superseded_at = now
        interest_cov = min(covered, r.interest)
        principal_cov = money(covered - interest_cov)
        rest_interest += money(r.interest - interest_cov)
        rest_principal += money(r.principal - principal_cov)
        if covered > ZERO:
            keep_number += 1
            new_rows.append(
                CreditInstallment(
                    clinic_id=clinic_id, number=keep_number, due_on=r.due_on,
                    principal=principal_cov, interest=interest_cov, amount=money(covered),
                )
            )
    rest_total = money(rest_principal + rest_interest)
    if rest_total <= ZERO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El crédito ya está pagado")

    # Renumerar: las sustituidas conservan su número histórico, las nuevas
    # continúan después de la mayor usada para no chocar.
    max_number = max((i.number for i in credit.installments), default=0)
    start = max_number + 1
    for i, row in enumerate(new_rows):
        row.number = start + i
    start += len(new_rows)

    count = payload.installment_count
    base_p = money(rest_principal / count)
    base_i = money(rest_interest / count)
    every = FREQUENCY_DAYS[payload.frequency]
    for i in range(count):
        p_part = base_p if i < count - 1 else money(rest_principal - base_p * (count - 1))
        i_part = base_i if i < count - 1 else money(rest_interest - base_i * (count - 1))
        new_rows.append(
            CreditInstallment(
                clinic_id=clinic_id, number=start + i, due_on=payload.first_due_on + timedelta(days=every * i),
                principal=p_part, interest=i_part, amount=money(p_part + i_part),
            )
        )
    credit.installments.extend(r for r in new_rows if r.amount > ZERO)
    credit.frequency = payload.frequency
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="restructure", entity_type="credit",
        entity_id=str(credit_id),
        after={"pending": str(rest_total), "installments": count, "first_due_on": str(payload.first_due_on)},
    )
    return await get_credit(db, clinic_id, credit_id)


async def void_credit(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, credit_id: uuid.UUID, reason: str
) -> CreditDetail:
    from app.modules.payments.service import void_charge

    credit = await _load(db, clinic_id, credit_id)
    payments = (await _payments(db, [credit.id])).get(credit.id, [])
    if any(p.voided_at is None for p in payments):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El crédito tiene cuotas pagadas: anule esos pagos primero o refinancie el saldo.",
        )
    apply_void(credit, actor_id, reason, "El crédito")
    if credit.interest_charge_id is not None:
        await void_charge(db, clinic_id, actor_id, credit.interest_charge_id, f"Crédito anulado: {reason.strip()}")
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="void", entity_type="credit",
        entity_id=str(credit_id), after={"reason": credit.void_reason},
    )
    return await get_credit(db, clinic_id, credit_id)
