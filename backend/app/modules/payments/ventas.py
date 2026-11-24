import csv
import io
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.patients.models import Patient
from app.modules.payments.constants import PAYMENT_METHODS, money
from app.modules.payments.models import Charge, Payment

ZERO = Decimal("0.00")
METODOS = {code: label for code, label, _ in PAYMENT_METHODS}


class PagoVenta(BaseModel):
    id: uuid.UUID
    fecha: date
    monto: Decimal
    medio: str
    medio_codigo: str
    referencia: str | None
    comprobante_id: uuid.UUID | None


class FacturaVenta(BaseModel):
    id: uuid.UUID
    numero: str
    estado: str
    fecha: date
    total: Decimal
    acreditado: Decimal


class Venta(BaseModel):
    id: uuid.UUID
    fecha: date
    patient_id: uuid.UUID
    paciente: str
    cedula: str | None
    descripcion: str
    origen: str
    monto: Decimal
    pagado: Decimal
    pendiente: Decimal
    estado_pago: str
    anulada: bool
    pagos: list[PagoVenta]
    factura: FacturaVenta | None
    facturable: bool
    motivo: str | None


class ResumenVentas(BaseModel):
    ventas: int
    vendido: Decimal
    cobrado: Decimal
    pendiente: Decimal
    facturado: Decimal
    sin_facturar: Decimal
    abonos_sin_asignar: Decimal
    pacientes: int


class Ventas(BaseModel):
    resumen: ResumenVentas
    items: list[Venta]
    facturacion_lista: bool
    faltantes: list[str]


async def listar(
    db: AsyncSession,
    user: CurrentUser,
    desde: date,
    hasta: date,
    q: str | None,
    pago: str | None,
    factura: str | None,
    patient_id: uuid.UUID | None,
    anuladas: bool,
) -> Ventas:
    from app.modules.invoicing.constants import FACTURA, VIGENTES
    from app.modules.invoicing.models import Invoice, InvoiceLine
    from app.modules.portal.models import PortalReceipt

    cid = user.clinic_id
    puede_facturas = user.has_permission("invoices:read")
    consulta = (
        select(Charge, Patient)
        .join(Patient, Patient.id == Charge.patient_id)
        .where(Charge.clinic_id == cid, Charge.issued_on >= desde, Charge.issued_on <= hasta)
        .order_by(Charge.issued_on.desc(), Charge.created_at.desc())
    )
    if not anuladas:
        consulta = consulta.where(Charge.voided_at.is_(None))
    if patient_id:
        consulta = consulta.where(Charge.patient_id == patient_id)
    if q and q.strip():
        t = f"%{q.strip()}%"
        consulta = consulta.where(
            or_(
                Charge.description.ilike(t),
                Patient.first_name.ilike(t),
                Patient.last_name.ilike(t),
                (Patient.first_name + " " + Patient.last_name).ilike(t),
                Patient.national_id.ilike(t),
            )
        )
    filas = (await db.execute(consulta)).all()
    ids = [c.id for c, _ in filas]

    pagos: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    comprobantes: dict[uuid.UUID, uuid.UUID] = {}
    if ids:
        for p in (
            await db.execute(
                select(Payment).where(Payment.charge_id.in_(ids), Payment.voided_at.is_(None)).order_by(Payment.received_on)
            )
        ).scalars():
            pagos[p.charge_id].append(p)
        pago_ids = [p.id for lista in pagos.values() for p in lista]
        if pago_ids:
            comprobantes = dict(
                (
                    await db.execute(
                        select(PortalReceipt.payment_id, PortalReceipt.id).where(PortalReceipt.payment_id.in_(pago_ids))
                    )
                ).all()
            )

    facturas: dict[uuid.UUID, FacturaVenta] = {}
    if ids:
        nota = aliased(Invoice)
        acreditado = (
            select(func.coalesce(func.sum(nota.total), 0))
            .where(nota.modified_invoice_id == Invoice.id, nota.status.in_(VIGENTES))
            .correlate(Invoice)
            .scalar_subquery()
        )
        for charge_id, inv, cred in (
            await db.execute(
                select(InvoiceLine.charge_id, Invoice, acreditado)
                .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
                .where(InvoiceLine.charge_id.in_(ids), Invoice.doc_type == FACTURA, Invoice.status.in_(VIGENTES))
                .order_by(Invoice.created_at)
            )
        ).all():
            facturas[charge_id] = FacturaVenta(
                id=inv.id, numero=inv.number, estado=inv.status, fecha=inv.issue_date, total=inv.total, acreditado=money(Decimal(cred)),
            )

    ortodoncia: set[uuid.UUID] = set()
    financiados: set[uuid.UUID] = set()
    if ids:
        from app.modules.credits.models import Credit
        from app.modules.orthodontics.models import OrthoCase

        ortodoncia = set((await db.execute(select(OrthoCase.charge_id).where(OrthoCase.charge_id.in_(ids)))).scalars())
        financiados = set((await db.execute(select(Credit.charge_id).where(Credit.charge_id.in_(ids)))).scalars())

    items: list[Venta] = []
    for c, p in filas:
        lista = pagos.get(c.id, [])
        pagado = money(sum((x.amount for x in lista), ZERO))
        pendiente = money(max(ZERO, Decimal(c.amount) - pagado))
        anulada = c.voided_at is not None
        estado = "anulada" if anulada else "pagada" if pendiente <= 0 else "parcial" if pagado > 0 else "pendiente"
        fv = facturas.get(c.id)
        acreditada = fv is not None and fv.acreditado >= fv.total
        motivo = None
        if anulada:
            motivo = "Venta anulada"
        elif fv and not acreditada:
            motivo = f"Ya facturada ({fv.numero})"
        facturable = motivo is None
        origen = (
            "ortodoncia" if c.id in ortodoncia else "credito" if c.id in financiados else "presupuesto" if c.budget_id else "manual"
        )
        items.append(Venta(
            id=c.id, fecha=c.issued_on, patient_id=p.id, paciente=f"{p.first_name} {p.last_name}", cedula=p.national_id,
            descripcion=c.description, origen=origen, monto=money(c.amount), pagado=pagado, pendiente=pendiente,
            estado_pago=estado, anulada=anulada,
            pagos=[
                PagoVenta(
                    id=x.id, fecha=x.received_on, monto=money(x.amount), medio=METODOS.get(x.method, x.method),
                    medio_codigo=x.method, referencia=x.reference, comprobante_id=comprobantes.get(x.id),
                )
                for x in lista
            ],
            factura=(fv if puede_facturas else None) if fv and not acreditada else None,
            facturable=facturable,
            motivo=motivo,
        ))

    if pago:
        items = [v for v in items if v.estado_pago == pago]
    if factura == "facturada":
        items = [v for v in items if v.factura is not None]
    elif factura == "sin_facturar":
        items = [v for v in items if v.facturable]

    vivas = [v for v in items if not v.anulada]
    sin_asignar = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.clinic_id == cid, Payment.charge_id.is_(None), Payment.voided_at.is_(None),
            Payment.received_on >= desde, Payment.received_on <= hasta,
            *( [Payment.patient_id == patient_id] if patient_id else [] ),
        )
    )
    resumen = ResumenVentas(
        ventas=len(vivas),
        vendido=money(sum((v.monto for v in vivas), ZERO)),
        cobrado=money(sum((v.pagado for v in vivas), ZERO)),
        pendiente=money(sum((v.pendiente for v in vivas), ZERO)),
        facturado=money(sum((v.monto for v in vivas if v.factura), ZERO)),
        sin_facturar=money(sum((v.monto for v in vivas if v.facturable), ZERO)),
        abonos_sin_asignar=money(Decimal(sin_asignar or 0)),
        pacientes=len({v.patient_id for v in vivas}),
    )

    lista_ok, faltan = True, []
    if user.has_permission("invoices:write"):
        from app.modules.invoicing import service as facturacion

        clinica = await facturacion._clinica(db, cid)
        conf = await facturacion._config(db, cid)
        faltan = facturacion._faltantes(clinica, conf)
        lista_ok = not faltan
    else:
        lista_ok = False
    return Ventas(resumen=resumen, items=items, facturacion_lista=lista_ok, faltantes=faltan)


router = APIRouter(prefix="/api/v1/sales", tags=["payments"])


def _rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = date.today()
    return desde or hoy.replace(day=1), hasta or hoy


@router.get("", response_model=Ventas)
async def get_ventas(
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = Query(default=None, max_length=120),
    pago: str | None = Query(default=None, pattern="^(pendiente|parcial|pagada|anulada)$"),
    factura: str | None = Query(default=None, pattern="^(facturada|sin_facturar)$"),
    patient_id: uuid.UUID | None = None,
    anuladas: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    d, h = _rango(desde, hasta)
    return await listar(db, current_user, d, h, q, pago, factura, patient_id, anuladas or pago == "anulada")


@router.get("/export.csv")
async def get_ventas_csv(
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = Query(default=None, max_length=120),
    pago: str | None = Query(default=None, pattern="^(pendiente|parcial|pagada|anulada)$"),
    factura: str | None = Query(default=None, pattern="^(facturada|sin_facturar)$"),
    patient_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    d, h = _rango(desde, hasta)
    v = await listar(db, current_user, d, h, q, pago, factura, patient_id, pago == "anulada")
    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";")
    w.writerow(["Fecha", "Paciente", "Cédula", "Concepto", "Origen", "Valor", "Cobrado", "Pendiente", "Estado", "Factura", "Estado factura", "Pagos (fecha · medio · referencia · monto)"])
    for x in v.items:
        w.writerow([
            x.fecha.isoformat(), x.paciente, x.cedula or "", x.descripcion, x.origen,
            str(x.monto).replace(".", ","), str(x.pagado).replace(".", ","), str(x.pendiente).replace(".", ","), x.estado_pago,
            x.factura.numero if x.factura else ("" if x.facturable else x.motivo or ""), x.factura.estado if x.factura else "",
            " | ".join(f"{p.fecha.isoformat()} · {p.medio} · {p.referencia or '-'} · {str(p.monto).replace('.', ',')}" for p in x.pagos),
        ])
    nombre = f"ventas-{d.isoformat()}-a-{h.isoformat()}.csv"
    return Response(
        "﻿" + salida.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )

