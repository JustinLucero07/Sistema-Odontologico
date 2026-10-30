"""RIDE: la representación impresa (PDF) del comprobante electrónico, que es lo
que recibe el paciente. Lleva la clave de acceso en código de barras."""

import base64
import io
from decimal import Decimal

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.invoicing.constants import AMBIENTES, FACTURA, FORMAS_PAGO, IVA, TIPOS_IDENTIFICACION

TINTA = colors.HexColor("#14242B")
SUAVE = colors.HexColor("#5B6B70")
LINEA = colors.HexColor("#D9D4CA")
FONDO = colors.HexColor("#F6F4EF")


def _p(texto: str, tam: float = 8.5, negrita: bool = False, color=TINTA, alinear: int = 0) -> Paragraph:
    estilo = ParagraphStyle(
        "x", fontName="Helvetica-Bold" if negrita else "Helvetica", fontSize=tam, leading=tam * 1.3, textColor=color, alignment=alinear
    )
    return Paragraph(texto.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>"), estilo)


def _dinero(v: Decimal) -> str:
    return f"{Decimal(v):,.2f}"


def _logo(data_url: str | None, ancho: float) -> Image | None:
    if not data_url or "," not in data_url:
        return None
    try:
        crudo = base64.b64decode(data_url.split(",", 1)[1])
        lector = ImageReader(io.BytesIO(crudo))
        w, h = lector.getSize()
        alto = ancho * h / w
        if alto > 28 * mm:
            ancho, alto = ancho * (28 * mm) / alto, 28 * mm
        return Image(io.BytesIO(crudo), width=ancho, height=alto)
    except Exception:
        return None


def generar(factura, clinica, modificada=None) -> bytes:
    """`factura` es un Invoice con sus líneas; `clinica` la Clinic emisora;
    `modificada` la factura original si es una nota de crédito."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    ancho = A4[0] - 28 * mm
    es_factura = factura.doc_type == FACTURA
    titulo = "FACTURA" if es_factura else "NOTA DE CRÉDITO"
    autorizada = factura.authorized_at is not None

    emisor = [
        _p(clinica.legal_name or clinica.name, 11, True),
        _p(clinica.name if clinica.legal_name and clinica.name != clinica.legal_name else "", 9, color=SUAVE),
        Spacer(0, 3),
        _p(f"Dirección matriz: {clinica.address or '—'}"),
        _p(f"Obligado a llevar contabilidad: {'SI' if clinica.keeps_accounting else 'NO'}"),
    ]
    if clinica.special_taxpayer:
        emisor.append(_p(f"Contribuyente especial Nro.: {clinica.special_taxpayer}"))
    if clinica.tax_regime and clinica.tax_regime.startswith("rimpe"):
        emisor.append(_p("CONTRIBUYENTE RÉGIMEN RIMPE" if clinica.tax_regime == "rimpe_emprendedor" else "CONTRIBUYENTE NEGOCIO POPULAR - RÉGIMEN RIMPE", 8, True))
    logo = _logo(clinica.logo_data, 50 * mm)
    izquierda = ([logo, Spacer(0, 4)] if logo else []) + emisor

    barras = code128.Code128(factura.access_key, barHeight=11 * mm, barWidth=0.62)
    derecha = [
        _p(f"R.U.C.: {clinica.tax_id}", 10, True),
        _p(titulo, 13, True),
        _p(f"No. {factura.number}", 10, True),
        Spacer(0, 4),
        _p("NÚMERO DE AUTORIZACIÓN", 7.5, True, SUAVE),
        _p(factura.access_key if autorizada else "PENDIENTE DE AUTORIZACIÓN", 7.5),
        _p(f"FECHA Y HORA DE AUTORIZACIÓN: {factura.authorized_at:%d/%m/%Y %H:%M:%S}" if autorizada else "", 7.5),
        _p(f"AMBIENTE: {AMBIENTES.get(factura.environment, '').upper()}    EMISIÓN: NORMAL", 7.5),
        Spacer(0, 4),
        _p("CLAVE DE ACCESO", 7.5, True, SUAVE),
        barras,
        _p(factura.access_key, 7, alinear=1),
    ]
    cabecera = Table([[izquierda, derecha]], colWidths=[ancho * 0.5, ancho * 0.5])
    cabecera.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (1, 0), (1, 0), 0.6, LINEA),
        ("BACKGROUND", (1, 0), (1, 0), FONDO),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    filas_comprador = [
        [_p("Razón social / Nombres:", 8, True), _p(factura.buyer_name), _p("Identificación:", 8, True), _p(f"{factura.buyer_id} ({TIPOS_IDENTIFICACION.get(factura.buyer_id_type, '')})")],
        [_p("Fecha de emisión:", 8, True), _p(f"{factura.issue_date:%d/%m/%Y}"), _p("Dirección:", 8, True), _p(factura.buyer_address or "—")],
    ]
    if not es_factura and modificada is not None:
        filas_comprador.append([
            _p("Comprobante que modifica:", 8, True), _p(f"FACTURA {modificada.number} del {modificada.issue_date:%d/%m/%Y}"),
            _p("Motivo:", 8, True), _p(factura.reason or ""),
        ])
    comprador = Table(filas_comprador, colWidths=[ancho * 0.18, ancho * 0.37, ancho * 0.15, ancho * 0.30])
    comprador.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINEA), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

    detalle = [[_p("Código", 8, True), _p("Descripción", 8, True)] + [_p(t, 8, True, alinear=2) for t in ["Cant.", "P. unitario", "Desc.", "Total"]]]
    for ln in factura.lines:
        detalle.append([
            _p(ln.code), _p(ln.description),
            _p(f"{Decimal(ln.quantity).normalize():f}", alinear=2), _p(_dinero(ln.unit_price), alinear=2),
            _p(_dinero(ln.discount), alinear=2), _p(_dinero(ln.subtotal), alinear=2),
        ])
    tabla = Table(detalle, colWidths=[ancho * 0.12, ancho * 0.46, ancho * 0.08, ancho * 0.12, ancho * 0.1, ancho * 0.12], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FONDO),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    bases: dict[str, Decimal] = {}
    ivas: dict[str, Decimal] = {}
    for ln in factura.lines:
        bases[ln.vat_code] = bases.get(ln.vat_code, Decimal(0)) + Decimal(ln.subtotal)
        ivas[ln.vat_code] = ivas.get(ln.vat_code, Decimal(0)) + Decimal(ln.vat)
    totales = []
    for codigo, (etiqueta, _) in IVA.items():
        if codigo in bases:
            nombre = etiqueta.replace("IVA ", "") if codigo in ("0", "4", "5") else etiqueta
            totales.append(["SUBTOTAL " + nombre.upper(), _dinero(bases[codigo])])
    totales.append(["SUBTOTAL SIN IMPUESTOS", _dinero(factura.subtotal)])
    totales.append(["DESCUENTO", _dinero(factura.discount)])
    for codigo, valor in ivas.items():
        if valor:
            totales.append([IVA[codigo][0].upper(), _dinero(valor)])
    totales.append(["VALOR TOTAL" if es_factura else "VALOR MODIFICACIÓN", _dinero(factura.total)])
    caja_totales = Table([[_p(a, 8, True), _p(b, 8.5, alinear=2)] for a, b in totales], colWidths=[ancho * 0.25, ancho * 0.15])
    caja_totales.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
        ("BACKGROUND", (0, -1), (-1, -1), FONDO),
    ]))

    adicional = [[_p("Información adicional", 8, True)]]
    for nombre, valor in (("Correo", factura.buyer_email), ("Teléfono", factura.buyer_phone), ("Observación", factura.notes)):
        if valor:
            adicional.append([_p(f"{nombre}: {valor}")])
    if es_factura:
        adicional.append([_p(f"Forma de pago: {FORMAS_PAGO.get(factura.payment_method, factura.payment_method)} — {_dinero(factura.total)}")])
    caja_adicional = Table(adicional, colWidths=[ancho * 0.55])
    caja_adicional.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINEA)]))
    pie = Table([[caja_adicional, caja_totales]], colWidths=[ancho * 0.58, ancho * 0.42])
    pie.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    doc.build([cabecera, Spacer(0, 8), comprador, Spacer(0, 8), tabla, Spacer(0, 8), pie])
    return buf.getvalue()
