import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.invoicing import service
from app.modules.invoicing.constants import AMBIENTES, ESTADOS, FORMAS_PAGO, IVA, TIPOS_IDENTIFICACION
from app.modules.invoicing.models import Invoice
from app.modules.invoicing.schemas import (
    CreditNoteCreate,
    DiscardRequest,
    EmailRequest,
    InvoiceableCharge,
    InvoiceCreate,
    InvoiceOut,
    SettingsOut,
    SettingsUpdate,
)
from app.shared.archivos import cabeceras_archivo

router = APIRouter(prefix="/api/v1/invoices", tags=["invoicing"])
settings_router = APIRouter(prefix="/api/v1/invoicing", tags=["invoicing"])
patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}", tags=["invoicing"])


async def _salida(db: AsyncSession, factura: Invoice) -> InvoiceOut:
    out = InvoiceOut.model_validate(factura)
    out.number = factura.number
    if factura.doc_type == "01":
        out.credited = await service.acreditado(db, factura)
    return out


# ---------------------------------------------------------------- Configuración


@settings_router.get("/catalogs")
async def get_catalogs(current_user: CurrentUser = Depends(require_permission("invoices:read"))):
    def lista(d):
        return [{"code": k, "label": v if isinstance(v, str) else v[0]} for k, v in d.items()]

    return {
        "vat": [{"code": k, "label": v[0], "rate": str(v[1])} for k, v in IVA.items()],
        "id_types": lista(TIPOS_IDENTIFICACION),
        "payment_methods": lista(FORMAS_PAGO),
        "statuses": lista(ESTADOS),
        "environments": lista(AMBIENTES),
    }


@settings_router.get("/settings", response_model=SettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    out = await service.get_settings(db, current_user.clinic_id)
    await db.commit()
    return out


@settings_router.put("/settings", response_model=SettingsOut)
async def put_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.update_settings(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return out


@settings_router.post("/certificate", response_model=SettingsOut)
async def post_certificate(
    file: UploadFile = File(...),
    password: str = Form(..., min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    contenido = await file.read(100_001)
    out = await service.upload_certificate(db, current_user.clinic_id, current_user.id, contenido, password)
    await db.commit()
    return out


@settings_router.delete("/certificate", response_model=SettingsOut)
async def delete_certificate(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.delete_certificate(db, current_user.clinic_id, current_user.id)
    await db.commit()
    return out


# ---------------------------------------------------------------- Comprobantes


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    status: str | None = None,
    doc_type: str | None = None,
    patient_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    filas = await service.list_invoices(
        db, current_user.clinic_id, estado=status, tipo=doc_type, paciente=patient_id, desde=date_from, hasta=date_to, texto=q, limit=limit
    )
    return [await _salida(db, f) for f in filas]


@router.post("", response_model=InvoiceOut, status_code=201)
async def post_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    factura = await service.create_invoice(db, current_user.clinic_id, current_user.id, payload)
    # Primero queda guardada con su número; después se intenta con el SRI.
    # Si el SRI no responde, el proceso en segundo plano la retoma.
    await db.commit()
    await service.process_and_notify(db, factura)
    await db.commit()
    return await _salida(db, factura)


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    return await _salida(db, await service.get_invoice_or_404(db, current_user.clinic_id, invoice_id))


@router.post("/{invoice_id}/retry", response_model=InvoiceOut)
async def post_retry(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    factura = await service.retry(db, current_user.clinic_id, current_user.id, invoice_id)
    await db.commit()
    return await _salida(db, factura)


@router.post("/{invoice_id}/discard", response_model=InvoiceOut)
async def post_discard(
    invoice_id: uuid.UUID,
    payload: DiscardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    factura = await service.discard(db, current_user.clinic_id, current_user.id, invoice_id, payload.reason)
    await db.commit()
    return await _salida(db, factura)


@router.post("/{invoice_id}/credit-note", response_model=InvoiceOut, status_code=201)
async def post_credit_note(
    invoice_id: uuid.UUID,
    payload: CreditNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    nota = await service.create_credit_note(db, current_user.clinic_id, current_user.id, invoice_id, payload)
    await db.commit()
    await service.process_and_notify(db, nota)
    await db.commit()
    return await _salida(db, nota)


@router.post("/{invoice_id}/email", response_model=InvoiceOut)
async def post_email(
    invoice_id: uuid.UUID,
    payload: EmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    factura = await service.get_invoice_or_404(db, current_user.clinic_id, invoice_id)
    await service.send_email(db, factura, payload.email)
    await db.commit()
    return await _salida(db, factura)


@router.get("/{invoice_id}/pdf")
async def get_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    factura = await service.get_invoice_or_404(db, current_user.clinic_id, invoice_id)
    return Response(
        await service.pdf(db, factura), media_type="application/pdf",
        headers=cabeceras_archivo(service.nombre_archivo(factura, "pdf"), en_linea=True),
    )


@router.get("/{invoice_id}/xml")
async def get_xml(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    factura = await service.get_invoice_or_404(db, current_user.clinic_id, invoice_id)
    contenido = factura.authorized_xml or factura.signed_xml
    if not contenido:
        return Response(status_code=404, content='{"detail":"El comprobante aún no tiene XML."}', media_type="application/json")
    return Response(
        contenido.encode(), media_type="application/xml",
        headers=cabeceras_archivo(service.nombre_archivo(factura, "xml"), en_linea=False),
    )


# ---------------------------------------------------------------- Por paciente


@patient_router.get("/invoices", response_model=list[InvoiceOut])
async def get_patient_invoices(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    from app.modules.patients.service import get_patient_or_404

    await get_patient_or_404(db, current_user.clinic_id, patient_id)
    filas = await service.list_invoices(db, current_user.clinic_id, paciente=patient_id)
    return [await _salida(db, f) for f in filas]


@patient_router.get("/invoiceable-charges", response_model=list[InvoiceableCharge])
async def get_invoiceable(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:read")),
):
    return await service.invoiceable_charges(db, current_user.clinic_id, patient_id)
