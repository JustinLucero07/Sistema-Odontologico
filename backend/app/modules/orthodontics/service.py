import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.orthodontics.constants import DOC_FIELDS, MAX_CONTROLS
from app.modules.orthodontics.models import OrthoCase, OrthoControl
from app.modules.orthodontics.schemas import (
    CaseCreate,
    CaseDetail,
    CaseList,
    CaseOut,
    CaseUpdate,
    ControlCreate,
    ControlOut,
    ControlPayment,
    ControlsGenerate,
    ControlUpdate,
    PatientMini,
    PaymentLine,
)
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.modules.payments import service as payments
from app.modules.payments.constants import money
from app.modules.payments.models import Charge, Payment
from app.modules.payments.schemas import ChargeCreate, PaymentCreate
from app.modules.professionals.models import Professional

ZERO = Decimal("0.00")
OPEN_STATUSES = {"activo", "retencion", "pausa"}


def code_for(number: int) -> str:
    return f"ORT-{number:04d}"


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return date(year, month, 28)


async def _payments_by_charge(db: AsyncSession, charge_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Payment]]:
    if not charge_ids:
        return {}
    rows = (
        await db.execute(select(Payment).where(Payment.charge_id.in_(charge_ids)).order_by(Payment.received_on, Payment.created_at))
    ).scalars().all()
    out: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for p in rows:
        out[p.charge_id].append(p)
    return out


async def _professional_names(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = (await db.execute(select(Professional).where(Professional.id.in_(ids)))).scalars().all()
    return {p.id: f"{p.first_name} {p.last_name}".strip() for p in rows}


def _control_out(c: OrthoControl, pays: list[Payment], today: date) -> ControlOut:
    live = [p for p in pays if p.voided_at is None]
    paid = money(sum((p.amount for p in live), ZERO))
    amount = money(c.amount or ZERO)
    balance = money(max(amount - paid, ZERO))
    if amount == ZERO:
        estado = "sin_valor" if paid == ZERO else "pagada"
    elif balance == ZERO:
        estado = "pagada"
    elif c.due_on and c.due_on < today:
        estado = "vencida"
    elif paid > ZERO:
        estado = "parcial"
    else:
        estado = "pendiente"
    return ControlOut(
        id=c.id, number=c.number, planned_on=c.planned_on, attended_on=c.attended_on, planning=c.planning,
        arches=c.arches, elastics=c.elastics, tads=c.tads, due_on=c.due_on, amount=amount, notes=c.notes,
        paid=paid, balance=balance, status=estado,
        payments=[PaymentLine.model_validate(p) for p in pays],
    )


def _case_out(
    case: OrthoCase, patient: Patient, prof_name: str | None, pays: list[Payment], today: date, detail: bool = False
) -> CaseOut | CaseDetail:
    live = [p for p in pays if p.voided_at is None]
    paid = money(sum((p.amount for p in live), ZERO))
    agreed = money(case.agreed_total or ZERO)
    controls = list(case.controls)
    controls_total = money(sum((c.amount or ZERO for c in controls), ZERO))
    by_control: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for p in pays:
        if p.ortho_control_id:
            by_control[p.ortho_control_id].append(p)
    control_outs = [_control_out(c, by_control.get(c.id, []), today) for c in controls]

    attended = [c.attended_on for c in controls if c.attended_on]
    upcoming = sorted(c.planned_on for c in controls if c.planned_on and not c.attended_on)
    next_on = next((d for d in upcoming if d >= today), None)
    overdue = bool(upcoming and upcoming[0] < today)
    if overdue:
        next_on = upcoming[0]

    data = dict(
        id=case.id, number=case.number, code=code_for(case.number),
        patient=PatientMini(
            id=patient.id, first_name=patient.first_name, last_name=patient.last_name,
            national_id=patient.national_id, phone=patient.phone, whatsapp=patient.whatsapp,
        ),
        professional_id=case.professional_id, professional_name=prof_name, charge_id=case.charge_id,
        status=case.status, stage=case.stage, needs_review=case.needs_review, has_tad=case.has_tad,
        appliance=case.appliance, started_on=case.started_on, estimated_months=case.estimated_months,
        agreed_total=agreed, special_attention=case.special_attention,
        special_attention_note=case.special_attention_note,
        doc_xrays=case.doc_xrays, doc_photos=case.doc_photos, doc_models=case.doc_models,
        doc_folder=case.doc_folder, doc_notes=case.doc_notes or {}, notes=case.notes,
        paid=paid, balance=money(max(agreed - paid, ZERO)), controls_total=controls_total,
        difference=money(controls_total - agreed) if controls else ZERO,
        controls_count=len(controls), controls_paid=sum(1 for c in control_outs if c.status == "pagada" and c.amount > 0),
        last_control_on=max(attended) if attended else None, next_control_on=next_on,
        next_control_overdue=overdue,
        docs_pending=sum(1 for f, _ in DOC_FIELDS if getattr(case, f) in ("por_revisar", "pendiente")),
    )
    if not detail:
        return CaseOut(**data)
    unassigned = money(sum((p.amount for p in live if p.ortho_control_id is None), ZERO))
    return CaseDetail(**data, controls=control_outs, unassigned_paid=unassigned)


async def _get_case(db: AsyncSession, clinic_id: uuid.UUID, case_id: uuid.UUID) -> OrthoCase:
    case = (
        await db.execute(
            select(OrthoCase)
            .where(OrthoCase.id == case_id, OrthoCase.clinic_id == clinic_id)
            .options(selectinload(OrthoCase.controls))
        )
    ).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de ortodoncia no encontrada")
    return case


async def get_case(db: AsyncSession, clinic_id: uuid.UUID, case_id: uuid.UUID) -> CaseDetail:
    db.expire_all()
    case = await _get_case(db, clinic_id, case_id)
    patient = await db.get(Patient, case.patient_id)
    names = await _professional_names(db, {case.professional_id} if case.professional_id else set())
    pays = (await _payments_by_charge(db, [case.charge_id] if case.charge_id else [])).get(case.charge_id, [])
    return _case_out(case, patient, names.get(case.professional_id), pays, date.today(), detail=True)


async def cases_for_patient(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[CaseOut]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await list_cases(db, clinic_id, patient_id=patient_id, include_closed=True)
    return result.items


async def list_cases(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    q: str | None = None,
    status_: str | None = None,
    has_tad: str | None = None,
    docs: str | None = None,
    next_control: str | None = None,
    special_attention: bool | None = None,
    needs_review: bool | None = None,
    professional_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
    include_closed: bool = True,
) -> CaseList:
    query = (
        select(OrthoCase, Patient)
        .join(Patient, Patient.id == OrthoCase.patient_id)
        .where(OrthoCase.clinic_id == clinic_id, Patient.deleted_at.is_(None))
        .options(selectinload(OrthoCase.controls))
        .order_by(OrthoCase.number)
    )
    if patient_id:
        query = query.where(OrthoCase.patient_id == patient_id)
    rows = (await db.execute(query)).all()
    all_cases = [c for c, _ in rows]
    active = sum(1 for c in all_cases if c.status in OPEN_STATUSES)

    pays = await _payments_by_charge(db, [c.charge_id for c in all_cases if c.charge_id])
    names = await _professional_names(db, {c.professional_id for c in all_cases if c.professional_id})
    today = date.today()

    termino = (q or "").strip().lower()
    items: list[CaseOut] = []
    for case, patient in rows:
        if status_ == "abiertos" and case.status not in OPEN_STATUSES:
            continue
        if status_ == "cerrados" and case.status in OPEN_STATUSES:
            continue
        if status_ and status_ not in ("abiertos", "cerrados") and case.status != status_:
            continue
        if has_tad and case.has_tad != has_tad:
            continue
        if special_attention is not None and case.special_attention != special_attention:
            continue
        if needs_review is not None and case.needs_review != needs_review:
            continue
        if professional_id and case.professional_id != professional_id:
            continue
        if termino:
            texto = f"{patient.first_name} {patient.last_name} {patient.national_id or ''} {code_for(case.number)}".lower()
            if not all(t in texto for t in termino.split()):
                continue
        out = _case_out(case, patient, names.get(case.professional_id), pays.get(case.charge_id, []), today)
        if docs == "pendiente" and out.docs_pending == 0:
            continue
        if docs == "completa" and out.docs_pending > 0:
            continue
        if next_control == "sin_fecha" and out.next_control_on is not None:
            continue
        if next_control == "vencido" and not out.next_control_overdue:
            continue
        if next_control == "semana" and not (
            out.next_control_on and not out.next_control_overdue and out.next_control_on <= today + timedelta(days=7)
        ):
            continue
        if next_control == "mes" and not (
            out.next_control_on and not out.next_control_overdue and out.next_control_on <= today + timedelta(days=31)
        ):
            continue
        if next_control == "con_saldo" and out.balance <= 0:
            continue
        items.append(out)
    return CaseList(items=items, total=len(all_cases), active=active, inactive=len(all_cases) - active)


async def _sync_charge(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, case: OrthoCase, patient: Patient
) -> None:
    total = money(case.agreed_total or ZERO)
    if case.charge_id is None:
        if total <= ZERO:
            return
        charge = await payments.create_charge(
            db, clinic_id, actor_id, patient.id,
            ChargeCreate(description=f"Tratamiento de ortodoncia {code_for(case.number)}", amount=total,
                         issued_on=case.started_on or date.today()),
        )
        case.charge_id = charge.id
        return
    charge = await db.get(Charge, case.charge_id)
    if charge is None or charge.voided_at is not None:
        case.charge_id = None
        await _sync_charge(db, clinic_id, actor_id, case, patient)
        return
    if total == money(charge.amount):
        return
    pagado = money(
        await db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.charge_id == charge.id, Payment.voided_at.is_(None)
            )
        )
        or ZERO
    )
    if total < pagado or total <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El valor del tratamiento no puede ser menor que lo ya abonado (${pagado}).",
        )
    from app.modules.invoicing.service import charge_is_invoiced

    if await charge_is_invoiced(db, charge.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El tratamiento ya está facturado: el valor no se puede cambiar.",
        )
    antes = str(charge.amount)
    charge.amount = total
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="charge",
        entity_id=str(charge.id), before={"amount": antes}, after={"amount": str(total), "motivo": "valor de ortodoncia"},
    )


async def create_case(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: CaseCreate) -> CaseDetail:
    patient = await get_patient_or_404(db, clinic_id, payload.patient_id)
    abierta = await db.scalar(
        select(OrthoCase.id).where(
            OrthoCase.clinic_id == clinic_id, OrthoCase.patient_id == patient.id,
            OrthoCase.status.in_(OPEN_STATUSES),
        )
    )
    if abierta:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este paciente ya tiene una ficha de ortodoncia abierta.",
        )
    numero = (await db.scalar(select(func.max(OrthoCase.number)).where(OrthoCase.clinic_id == clinic_id)) or 0) + 1
    data = payload.model_dump(exclude_unset=True, exclude={"patient_id"})
    data = {k: v for k, v in data.items() if v is not None}
    case = OrthoCase(clinic_id=clinic_id, patient_id=patient.id, number=numero, doc_notes={}, **data)
    db.add(case)
    await db.flush()
    await _sync_charge(db, clinic_id, actor_id, case, patient)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="ortho_case",
        entity_id=str(case.id), after={"patient_id": str(patient.id), "number": code_for(numero)},
    )
    await db.flush()
    return await get_case(db, clinic_id, case.id)


async def update_case(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, case_id: uuid.UUID, payload: CaseUpdate
) -> CaseDetail:
    case = await _get_case(db, clinic_id, case_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is None and field in ("status", "needs_review", "has_tad", "agreed_total", "special_attention",
                                       "doc_xrays", "doc_photos", "doc_models", "doc_folder", "doc_notes"):
            continue
        setattr(case, field, value)
    if "status" in data and data["status"] in OPEN_STATUSES:
        otra = await db.scalar(
            select(OrthoCase.id).where(
                OrthoCase.clinic_id == clinic_id, OrthoCase.patient_id == case.patient_id,
                OrthoCase.status.in_(OPEN_STATUSES), OrthoCase.id != case.id,
            )
        )
        if otra:
            raise HTTPException(status_code=409, detail="El paciente ya tiene otra ficha de ortodoncia abierta.")
    if "agreed_total" in data and data["agreed_total"] is not None:
        patient = await db.get(Patient, case.patient_id)
        await _sync_charge(db, clinic_id, actor_id, case, patient)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="ortho_case",
        entity_id=str(case.id), after=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await db.flush()
    return await get_case(db, clinic_id, case.id)


async def delete_case(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, case_id: uuid.UUID) -> None:
    case = await _get_case(db, clinic_id, case_id)
    if case.charge_id:
        vivos = await db.scalar(
            select(func.count()).select_from(Payment).where(
                Payment.charge_id == case.charge_id, Payment.voided_at.is_(None)
            )
        )
        if vivos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La ficha tiene abonos registrados. Márquela como «Finalizado» o anule primero los pagos.",
            )
        charge = await db.get(Charge, case.charge_id)
        if charge is not None and charge.voided_at is None:
            await payments.void_charge(db, clinic_id, actor_id, charge.id, "Ficha de ortodoncia eliminada")
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="ortho_case",
        entity_id=str(case.id), after={"number": code_for(case.number)},
    )
    await db.delete(case)
    await db.flush()


async def _get_control(db: AsyncSession, clinic_id: uuid.UUID, control_id: uuid.UUID) -> OrthoControl:
    c = (
        await db.execute(select(OrthoControl).where(OrthoControl.id == control_id, OrthoControl.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuota no encontrada")
    return c


async def add_control(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, case_id: uuid.UUID, payload: ControlCreate
) -> CaseDetail:
    case = await _get_case(db, clinic_id, case_id)
    if len(case.controls) >= MAX_CONTROLS:
        raise HTTPException(status_code=422, detail=f"Máximo {MAX_CONTROLS} cuotas por ficha.")
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    numero = max((c.number for c in case.controls), default=0) + 1
    db.add(OrthoControl(clinic_id=clinic_id, case_id=case.id, number=numero, **data))
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="ortho_control",
        entity_id=str(case.id), after={"number": numero, **payload.model_dump(exclude_unset=True, mode="json")},
    )
    await db.flush()
    return await get_case(db, clinic_id, case.id)


async def generate_controls(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, case_id: uuid.UUID, payload: ControlsGenerate
) -> CaseDetail:
    case = await _get_case(db, clinic_id, case_id)
    if len(case.controls) + payload.count > MAX_CONTROLS:
        raise HTTPException(status_code=422, detail=f"Máximo {MAX_CONTROLS} cuotas por ficha.")
    numero = max((c.number for c in case.controls), default=0)
    for i in range(payload.count):
        fecha = (
            payload.first_on + timedelta(days=payload.every_days * i)
            if payload.every_days
            else _add_months(payload.first_on, i)
        )
        numero += 1
        db.add(OrthoControl(
            clinic_id=clinic_id, case_id=case.id, number=numero, planned_on=fecha, due_on=fecha,
            amount=money(payload.amount),
        ))
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="ortho_control",
        entity_id=str(case.id), after=payload.model_dump(mode="json"),
    )
    await db.flush()
    return await get_case(db, clinic_id, case.id)


async def update_control(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, control_id: uuid.UUID, payload: ControlUpdate
) -> CaseDetail:
    c = await _get_control(db, clinic_id, control_id)
    data = payload.model_dump(exclude_unset=True)
    if "amount" in data:
        if data["amount"] is None:
            data["amount"] = ZERO
        abonado = money(
            await db.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.ortho_control_id == c.id, Payment.voided_at.is_(None)
                )
            )
            or ZERO
        )
        if money(data["amount"]) < abonado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La cuota ya tiene ${abonado} abonados: su valor no puede ser menor.",
            )
    for field, value in data.items():
        setattr(c, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="ortho_control",
        entity_id=str(c.id), after=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await db.flush()
    return await get_case(db, clinic_id, c.case_id)


async def delete_control(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, control_id: uuid.UUID) -> CaseDetail:
    c = await _get_control(db, clinic_id, control_id)
    vivos = await db.scalar(
        select(func.count()).select_from(Payment).where(Payment.ortho_control_id == c.id, Payment.voided_at.is_(None))
    )
    if vivos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cuota tiene abonos. Anule primero los pagos para poder eliminarla.",
        )
    case_id = c.case_id
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="ortho_control",
        entity_id=str(c.id), after={"number": c.number},
    )
    await db.delete(c)
    await db.flush()
    # Renumerar para que la lista quede 01, 02, 03… sin huecos.
    restantes = (
        await db.execute(select(OrthoControl).where(OrthoControl.case_id == case_id).order_by(OrthoControl.number))
    ).scalars().all()
    for i, ctrl in enumerate(restantes, start=1):
        ctrl.number = i
    await db.flush()
    return await get_case(db, clinic_id, case_id)


async def pay_control(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, control_id: uuid.UUID, payload: ControlPayment
) -> CaseDetail:
    c = await _get_control(db, clinic_id, control_id)
    case = await _get_case(db, clinic_id, c.case_id)
    if case.charge_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Defina primero el valor del tratamiento para poder registrar abonos.",
        )
    abonado = money(
        await db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.ortho_control_id == c.id, Payment.voided_at.is_(None)
            )
        )
        or ZERO
    )
    saldo = money((c.amount or ZERO) - abonado)
    if c.amount and payload.amount > saldo:
        raise HTTPException(
            status_code=422,
            detail=f"El abono (${payload.amount}) supera el saldo de la cuota (${max(saldo, ZERO)}).",
        )
    datos = payload.model_dump()
    datos["charge_id"] = case.charge_id
    if not datos.get("notes"):
        datos["notes"] = f"Ortodoncia {code_for(case.number)} · cuota {c.number:02d}"
    pago = await payments.create_payment(db, clinic_id, actor_id, case.patient_id, PaymentCreate(**datos))
    pago.ortho_control_id = c.id
    await db.flush()
    return await get_case(db, clinic_id, case.id)
