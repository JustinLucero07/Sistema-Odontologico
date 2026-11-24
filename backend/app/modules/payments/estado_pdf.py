import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.clinics.models import Clinic
from app.modules.consents.pdf import LINEA, SUAVE, TINTA, _firma, _p
from app.modules.invoicing.ride import _logo
from app.modules.patients.service import get_patient_or_404
from app.modules.payment_accounts.service import list_accounts
from app.modules.payments import service
from app.modules.payments.constants import PAYMENT_METHODS
from app.shared.archivos import cabeceras_archivo

METODOS = {code: label for code, label, _ in PAYMENT_METHODS}
ESTADOS = {"pagada": "Pagado", "parcial": "Abonado", "pendiente": "Pendiente"}
FONDO = colors.HexColor("#F4F7F7")
OSCURO = colors.HexColor("#0F2427")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _dinero(v) -> str:
    return "$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fecha(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _tabla(filas: list[list], anchos: list[float], numericas: set[int]) -> Table:
    t = Table(filas, colWidths=anchos, repeatRows=1)
    estilo = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), SUAVE),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), TINTA),
        ("LINEBELOW", (0, 0), (-1, 0), 1, LINEA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#E8EEEE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for c in numericas:
        estilo.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(estilo))
    return t


def _cuenta(a, ancho: float) -> Table:
    tipo = {"ahorros": "Cuenta de ahorros", "corriente": "Cuenta corriente"}.get(a.account_type or "", "Cuenta")
    datos = [_p(a.label, 10, True)]
    if a.account_number:
        datos.append(_p(f"{tipo} N.º {a.account_number}", 9))
    if a.holder_name:
        datos.append(_p(f"Titular: {a.holder_name}", 8.5, color=SUAVE))
    if a.holder_id:
        datos.append(_p(f"C.I./RUC: {a.holder_id}", 8.5, color=SUAVE))
    if a.email:
        datos.append(_p(a.email, 8.5, color=SUAVE))
    if a.note:
        datos.append(_p(a.note, 8.5, color=SUAVE))
    qr = _firma(a.qr_data, 30 * mm) if a.qr_data else None
    if isinstance(qr, Image):
        lado = 30 * mm
        qr.drawWidth = lado
        qr.drawHeight = lado
        filas = [[qr, datos]]
        anchos = [34 * mm, ancho - 34 * mm]
    else:
        filas = [[datos]]
        anchos = [ancho]
    t = Table(filas, colWidths=anchos)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def generar(estado, paciente, clinica: Clinic, cuentas: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"Estado de cuenta · {paciente.first_name} {paciente.last_name}", author=clinica.name,
    )
    ancho = A4[0] - 36 * mm
    partes = []
    hoy = date.today()

    logo = _logo(clinica.logo_data, 34 * mm)
    cabecera = [_p(clinica.name, 13, True), _p(" · ".join(x for x in [clinica.address or "", clinica.phone or "", clinica.email or ""] if x), 8.5, color=SUAVE)]
    partes.append(Table([[logo, cabecera]], colWidths=[40 * mm, ancho - 40 * mm], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")]) if logo
                  else Table([[cabecera]], colWidths=[ancho]))
    partes.append(Spacer(0, 6))
    partes.append(_p("ESTADO DE CUENTA", 9, True, SUAVE))
    partes.append(_p(f"{paciente.first_name} {paciente.last_name}", 16, True))
    datos = f"Al {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}"
    if paciente.national_id:
        datos += f" · Cédula {paciente.national_id}"
    partes.append(_p(datos, 9.5, color=SUAVE))

    saldo = float(estado.balance)
    rotulo = "Saldo pendiente" if saldo > 0 else "Saldo a favor" if saldo < 0 else "Cuenta saldada"
    caja = lambda titulo, valor, oscuro=False: [  # noqa: E731
        _p(titulo, 8, color=colors.HexColor("#B8C7C8") if oscuro else SUAVE),
        _p(valor, 15, True, colors.white if oscuro else TINTA),
    ]
    tercio = ancho / 3
    totales = Table(
        [[caja("Total de tratamientos", _dinero(estado.total_charged)), caja("Total abonado", _dinero(estado.total_paid)),
          caja(rotulo, _dinero(abs(saldo)), True)]],
        colWidths=[tercio - 3 * mm, tercio - 3 * mm, tercio],
    )
    totales.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), FONDO),
        ("BACKGROUND", (2, 0), (2, 0), OSCURO),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    partes += [Spacer(0, 4), totales, Spacer(0, 10)]

    cargos = [c for c in estado.charges if c.voided_at is None]
    partes.append(_p("Tratamientos y cargos", 11, True))
    filas = [["FECHA", "CONCEPTO", "VALOR", "ABONADO", "PENDIENTE", "ESTADO"]]
    for c in cargos:
        filas.append([_fecha(c.issued_on), _p(c.description, 9), _dinero(c.amount), _dinero(c.paid), _dinero(c.pending), ESTADOS.get(c.status, c.status)])
    if len(filas) == 1:
        filas.append(["", "Sin cargos.", "", "", "", ""])
    partes += [_tabla(filas, [20 * mm, ancho - 100 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm], {2, 3, 4}), Spacer(0, 10)]

    pagos = [p for p in estado.payments if p.voided_at is None]
    partes.append(_p("Abonos recibidos", 11, True))
    filas = [["FECHA", "MEDIO DE PAGO", "REFERENCIA", "MONTO"]]
    for p in sorted(pagos, key=lambda x: x.received_on, reverse=True):
        filas.append([_fecha(p.received_on), METODOS.get(p.method, p.method), p.reference or "—", _dinero(p.amount)])
    if len(filas) == 1:
        filas.append(["", "Sin abonos.", "", ""])
    partes += [_tabla(filas, [24 * mm, 55 * mm, ancho - 109 * mm, 30 * mm], {3}), Spacer(0, 12)]

    if cuentas:
        bloque = [_p("Cómo pagar", 11, True)]
        texto = "Escanee el código con la app de su banco o transfiera a la cuenta, y envíe el comprobante a la clínica."
        if saldo > 0:
            texto = f"Valor pendiente: {_dinero(saldo)}. " + texto
        bloque.append(_p(texto, 9, color=SUAVE))
        mitad = (ancho - 6 * mm) / 2
        celdas = [_cuenta(a, mitad) for a in cuentas]
        filas = [celdas[i:i + 2] + ([""] if len(celdas[i:i + 2]) == 1 else []) for i in range(0, len(celdas), 2)]
        rejilla = Table(filas, colWidths=[mitad + 3 * mm, mitad + 3 * mm])
        rejilla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        bloque.append(rejilla)
        partes.append(KeepTogether(bloque))

    partes.append(Spacer(0, 8))
    partes.append(_p("Documento informativo de la cuenta del paciente. No reemplaza al comprobante de venta autorizado por el SRI.", 7.5, color=SUAVE))
    if clinica.document_footer:
        partes.append(_p(clinica.document_footer, 7.5, color=SUAVE, alinear=1))
    doc.build(partes)
    return buf.getvalue()


router = APIRouter(prefix="/api/v1/patients/{patient_id}", tags=["payments"])


@router.get("/statement.pdf")
async def get_statement_pdf(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    paciente = await get_patient_or_404(db, current_user.clinic_id, patient_id)
    estado = await service.get_statement(db, current_user.clinic_id, patient_id)
    clinica = await db.get(Clinic, current_user.clinic_id)
    cuentas = await list_accounts(db, current_user.clinic_id, only_active=True)
    nombre = f"estado-de-cuenta-{paciente.last_name}-{date.today():%Y%m%d}.pdf".replace(" ", "-")
    return Response(generar(estado, paciente, clinica, cuentas), media_type="application/pdf", headers=cabeceras_archivo(nombre, en_linea=True))
