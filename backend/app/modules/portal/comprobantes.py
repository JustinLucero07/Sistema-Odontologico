import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.shared.storage import get_storage
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.modules.payments import service as pagos
from app.modules.payments.constants import money
from app.modules.payments.models import Charge
from app.modules.payments.schemas import PaymentCreate
from app.modules.portal.models import PortalAccess, PortalReceipt
from app.shared.archivos import cabeceras_archivo, tipo_de_imagen

MAX_BYTES = 10 * 1024 * 1024
MAX_PENDIENTES = 5
ESTADOS = {"pendiente": "En revisión", "aceptado": "Aceptado", "rechazado": "Rechazado"}


def tipo_comprobante(contenido: bytes) -> str | None:
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    return tipo_de_imagen(contenido)


async def _control_del_paciente(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, control_id: uuid.UUID):
    from app.modules.orthodontics.models import OrthoCase, OrthoControl

    fila = (
        await db.execute(
            select(OrthoControl)
            .join(OrthoCase, OrthoCase.id == OrthoControl.case_id)
            .where(OrthoControl.id == control_id, OrthoCase.clinic_id == clinic_id, OrthoCase.patient_id == patient_id)
        )
    ).scalar_one_or_none()
    if fila is None:
        raise HTTPException(status_code=400, detail="La cuota elegida no es válida")
    return fila


async def crear_desde_portal(
    db: AsyncSession,
    access: PortalAccess,
    *,
    amount: Decimal,
    paid_on: date | None,
    reference: str | None,
    note: str | None,
    charge_id: uuid.UUID | None,
    ortho_control_id: uuid.UUID | None,
    filename: str,
    content: bytes,
) -> PortalReceipt:
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera los 10 MB")
    mime = tipo_comprobante(content)
    if mime is None:
        raise HTTPException(status_code=400, detail="Suba una foto (JPG, PNG) o un PDF del comprobante")
    if amount <= 0 or amount > Decimal("100000"):
        raise HTTPException(status_code=400, detail="El monto no es válido")
    if paid_on and paid_on > date.today():
        raise HTTPException(status_code=400, detail="La fecha del pago no puede ser futura")
    pendientes = await db.scalar(
        select(func.count()).select_from(PortalReceipt).where(
            PortalReceipt.patient_id == access.patient_id, PortalReceipt.status == "pendiente"
        )
    )
    if pendientes >= MAX_PENDIENTES:
        raise HTTPException(
            status_code=429,
            detail="Ya tiene varios comprobantes en revisión. Espere a que la clínica los revise.",
        )
    if charge_id:
        cargo = await db.get(Charge, charge_id)
        if cargo is None or cargo.patient_id != access.patient_id or cargo.clinic_id != access.clinic_id:
            raise HTTPException(status_code=400, detail="El concepto elegido no es válido")
    if ortho_control_id:
        await _control_del_paciente(db, access.clinic_id, access.patient_id, ortho_control_id)
        charge_id = None

    clave = await get_storage().save(access.clinic_id, filename or "comprobante", content)
    r = PortalReceipt(
        clinic_id=access.clinic_id,
        patient_id=access.patient_id,
        access_id=access.id,
        amount=money(amount),
        paid_on=paid_on or date.today(),
        reference=(reference or "").strip()[:120] or None,
        note=(note or "").strip()[:1000] or None,
        charge_id=charge_id,
        ortho_control_id=ortho_control_id,
        storage_key=clave,
        filename=(filename or "comprobante")[:255],
        mime_type=mime,
        size_bytes=len(content),
        status="pendiente",
        created_at=datetime.now(timezone.utc),
    )
    db.add(r)
    await db.flush()
    await record_audit(
        db, clinic_id=access.clinic_id, user_id=None, action="create", entity_type="portal_receipt",
        entity_id=str(r.id), after={"patient_id": str(access.patient_id), "amount": str(r.amount), "origen": "portal"},
    )
    return r


class ComprobanteOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str | None = None
    amount: Decimal
    paid_on: date
    reference: str | None
    note: str | None
    destino: str
    status: str
    status_label: str
    reject_reason: str | None
    payment_id: uuid.UUID | None
    mime_type: str
    created_at: datetime
    reviewed_at: datetime | None


async def _destinos(db: AsyncSession, rs: list[PortalReceipt]) -> dict[uuid.UUID, str]:
    from app.modules.orthodontics.models import OrthoCase, OrthoControl
    from app.modules.orthodontics.service import code_for

    out: dict[uuid.UUID, str] = {}
    cargos = {r.charge_id for r in rs if r.charge_id}
    controles = {r.ortho_control_id for r in rs if r.ortho_control_id}
    desc = dict((await db.execute(select(Charge.id, Charge.description).where(Charge.id.in_(cargos)))).all()) if cargos else {}
    ctrl = {}
    if controles:
        for cid, numero, caso in (
            await db.execute(
                select(OrthoControl.id, OrthoControl.number, OrthoCase.number)
                .join(OrthoCase, OrthoCase.id == OrthoControl.case_id)
                .where(OrthoControl.id.in_(controles))
            )
        ).all():
            ctrl[cid] = f"Ortodoncia {code_for(caso)} · cuota {numero:02d}"
    for r in rs:
        if r.ortho_control_id:
            out[r.id] = ctrl.get(r.ortho_control_id, "Cuota de ortodoncia")
        elif r.charge_id:
            out[r.id] = desc.get(r.charge_id, "Concepto")
        else:
            out[r.id] = "Abono a su cuenta"
    return out


async def a_salida(db: AsyncSession, rs: list[PortalReceipt], nombres: dict[uuid.UUID, str] | None = None) -> list[ComprobanteOut]:
    destinos = await _destinos(db, rs)
    return [
        ComprobanteOut(
            id=r.id, patient_id=r.patient_id, patient_name=(nombres or {}).get(r.patient_id),
            amount=r.amount, paid_on=r.paid_on, reference=r.reference, note=r.note, destino=destinos[r.id],
            status=r.status, status_label=ESTADOS.get(r.status, r.status), reject_reason=r.reject_reason,
            payment_id=r.payment_id, mime_type=r.mime_type, created_at=r.created_at, reviewed_at=r.reviewed_at,
        )
        for r in rs
    ]


async def del_paciente(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[PortalReceipt]:
    return list(
        (
            await db.execute(
                select(PortalReceipt)
                .where(PortalReceipt.clinic_id == clinic_id, PortalReceipt.patient_id == patient_id)
                .order_by(PortalReceipt.created_at.desc())
                .limit(30)
            )
        ).scalars().all()
    )


async def _obtener(db: AsyncSession, clinic_id: uuid.UUID, receipt_id: uuid.UUID) -> PortalReceipt:
    r = (
        await db.execute(select(PortalReceipt).where(PortalReceipt.id == receipt_id, PortalReceipt.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return r


class Aceptar(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    method: str = "transferencia"
    reference: str | None = Field(default=None, max_length=120)
    a_cuenta: bool = False


class Rechazar(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


router = APIRouter(prefix="/api/v1", tags=["portal"])


@router.get("/portal-receipts/pending", response_model=list[ComprobanteOut])
async def pendientes(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    rs = list(
        (
            await db.execute(
                select(PortalReceipt)
                .where(PortalReceipt.clinic_id == current_user.clinic_id, PortalReceipt.status == "pendiente")
                .order_by(PortalReceipt.created_at)
            )
        ).scalars().all()
    )
    ids = {r.patient_id for r in rs}
    nombres = {
        p.id: f"{p.first_name} {p.last_name}"
        for p in ((await db.execute(select(Patient).where(Patient.id.in_(ids)))).scalars().all() if ids else [])
    }
    return await a_salida(db, rs, nombres)


@router.get("/patients/{patient_id}/portal-receipts", response_model=list[ComprobanteOut])
async def del_paciente_route(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    await get_patient_or_404(db, current_user.clinic_id, patient_id)
    return await a_salida(db, await del_paciente(db, current_user.clinic_id, patient_id))


@router.get("/portal-receipts/{receipt_id}/file")
async def archivo(
    receipt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    r = await _obtener(db, current_user.clinic_id, receipt_id)
    contenido = await get_storage().read(r.storage_key)
    return Response(
        content=contenido, media_type=r.mime_type,
        headers={**cabeceras_archivo(r.filename, en_linea=True), "Cache-Control": "private, max-age=300"},
    )


@router.post("/portal-receipts/{receipt_id}/accept", response_model=ComprobanteOut)
async def aceptar(
    receipt_id: uuid.UUID,
    payload: Aceptar,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    r = await _obtener(db, current_user.clinic_id, receipt_id)
    if r.status != "pendiente":
        raise HTTPException(status_code=409, detail="Este comprobante ya fue revisado")
    monto = money(payload.amount or r.amount)
    referencia = payload.reference or r.reference or "Comprobante del portal"
    nota = "Comprobante enviado por el paciente desde el portal"
    if r.ortho_control_id and not payload.a_cuenta:
        from app.modules.orthodontics.schemas import ControlPayment
        from app.modules.orthodontics.service import pay_control

        control_id, rid = r.ortho_control_id, r.id
        await pay_control(
            db, current_user.clinic_id, current_user.id, control_id,
            ControlPayment(amount=monto, method=payload.method, reference=referencia, received_on=r.paid_on, notes=nota),
        )
        from app.modules.payments.models import Payment

        pago_id = await db.scalar(
            select(Payment.id).where(Payment.ortho_control_id == control_id).order_by(Payment.created_at.desc()).limit(1)
        )
        r = await _obtener(db, current_user.clinic_id, rid)
    else:
        pago = await pagos.create_payment(
            db, current_user.clinic_id, current_user.id, r.patient_id,
            PaymentCreate(
                amount=monto, method=payload.method, reference=referencia, received_on=r.paid_on, notes=nota,
                charge_id=None if payload.a_cuenta else r.charge_id,
            ),
        )
        pago_id = pago.id
    r.status = "aceptado"
    r.payment_id = pago_id
    r.reviewed_by_id = current_user.id
    r.reviewed_at = datetime.now(timezone.utc)
    await record_audit(
        db, clinic_id=current_user.clinic_id, user_id=current_user.id, action="accept", entity_type="portal_receipt",
        entity_id=str(r.id), after={"amount": str(monto), "payment_id": str(pago_id)},
    )
    await db.commit()
    return (await a_salida(db, [r]))[0]


@router.post("/portal-receipts/{receipt_id}/reject", response_model=ComprobanteOut)
async def rechazar(
    receipt_id: uuid.UUID,
    payload: Rechazar,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    r = await _obtener(db, current_user.clinic_id, receipt_id)
    if r.status != "pendiente":
        raise HTTPException(status_code=409, detail="Este comprobante ya fue revisado")
    r.status = "rechazado"
    r.reject_reason = payload.reason.strip()
    r.reviewed_by_id = current_user.id
    r.reviewed_at = datetime.now(timezone.utc)
    await record_audit(
        db, clinic_id=current_user.clinic_id, user_id=current_user.id, action="reject", entity_type="portal_receipt",
        entity_id=str(r.id), after={"reason": r.reject_reason},
    )
    await db.commit()
    return (await a_salida(db, [r]))[0]


async def avisar_clinica(receipt_id: uuid.UUID, proveedor=get_db) -> bool:
    from contextlib import aclosing

    async with aclosing(proveedor()) as sesiones:
        async for db in sesiones:
            return await avisar_con(db, receipt_id)
    return False


async def avisar_con(db: AsyncSession, receipt_id: uuid.UUID) -> bool:
    from app.core.config import get_settings
    from app.modules.clinics.models import Clinic
    from app.modules.mail import service as correo

    r = await db.get(PortalReceipt, receipt_id)
    if r is None:
        return False
    clinica = await db.get(Clinic, r.clinic_id)
    paciente = await db.get(Patient, r.patient_id)
    if not clinica or not clinica.email or not paciente:
        return False
    destino = (await _destinos(db, [r]))[r.id]
    nombre = f"{paciente.first_name} {paciente.last_name}"
    asunto = f"Comprobante de pago de {nombre}: {money(r.amount)} USD"
    lineas = [
        f"{correo.escapar(nombre)} envió un comprobante de pago desde su portal.",
        f"<b>Monto:</b> $ {money(r.amount)} · <b>Para:</b> {correo.escapar(destino)} · <b>Fecha del pago:</b> {r.paid_on:%d/%m/%Y}",
    ]
    if r.reference:
        lineas.append(f"<b>Referencia:</b> {correo.escapar(r.reference)}")
    if r.note:
        lineas.append(f"<b>Nota del paciente:</b> {correo.escapar(r.note)}")
    lineas.append("Revíselo en la ficha del paciente (pestaña Cuenta) o en el panel principal para aceptarlo o rechazarlo.")
    enlace = f"{get_settings().PORTAL_BASE_URL}/patients/{paciente.id}"
    texto = "\n".join(x.replace("<b>", "").replace("</b>", "") for x in lineas) + f"\n{enlace}"
    try:
        contenido = await get_storage().read(r.storage_key)
        await correo.enviar(
            db, clinica.id, clinica.email, asunto, texto,
            correo.pagina(clinica, "Llegó un comprobante de pago", lineas, ("Revisar comprobante", enlace)),
            adjuntos=[(r.filename, contenido, r.mime_type)],
        )
    except (correo.CorreoNoConfigurado, correo.CorreoFallido):
        return False
    return True
