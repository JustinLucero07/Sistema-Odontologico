"""PDF del consentimiento: el texto que se firmó, las firmas dibujadas y la
huella del contenido, para imprimir, archivar o entregar al paciente."""

import base64
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.invoicing.ride import _logo

TINTA = colors.HexColor("#14242B")
SUAVE = colors.HexColor("#5B6B70")
LINEA = colors.HexColor("#D9D4CA")


def _p(texto: str, tam: float = 10, negrita: bool = False, color=TINTA, alinear: int = 0, espacio: float = 1.45) -> Paragraph:
    estilo = ParagraphStyle(
        "c", fontName="Helvetica-Bold" if negrita else "Helvetica", fontSize=tam, leading=tam * espacio,
        textColor=color, alignment=alinear, spaceAfter=tam * 0.6,
    )
    seguro = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(seguro, estilo)


def _firma(data_url: str | None, ancho: float) -> Image | Paragraph:
    if not data_url:
        return Spacer(ancho, 22 * mm)
    try:
        crudo = base64.b64decode(data_url.split(",", 1)[1])
        img = Image(io.BytesIO(crudo))
        proporcion = img.imageHeight / img.imageWidth
        alto = min(26 * mm, ancho * proporcion)
        return Image(io.BytesIO(crudo), width=alto / proporcion, height=alto)
    except Exception:
        return Spacer(ancho, 22 * mm)


def generar(consent, paciente, clinica, profesional=None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=consent.title, author=clinica.name)
    ancho = A4[0] - 36 * mm
    partes = []

    logo = _logo(clinica.logo_data, 34 * mm)
    cabecera = [_p(clinica.name, 13, True), _p(" · ".join(x for x in [clinica.address or "", clinica.phone or ""] if x), 8.5, color=SUAVE)]
    partes.append(Table([[logo or "", cabecera]], colWidths=[40 * mm, ancho - 40 * mm], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")]) if logo
                  else Table([[cabecera]], colWidths=[ancho]))
    partes.append(Spacer(0, 6))
    partes.append(_p("CONSENTIMIENTO INFORMADO", 9, True, SUAVE))
    partes.append(_p(consent.title, 16, True))
    datos = f"Paciente: {paciente.first_name} {paciente.last_name}"
    if paciente.national_id:
        datos += f" · Cédula {paciente.national_id}"
    if consent.tooth:
        datos += f" · Pieza/zona: {consent.tooth}"
    partes.append(_p(datos, 9.5, color=SUAVE))
    partes.append(Spacer(0, 4))
    for parrafo in consent.body.split("\n"):
        if parrafo.strip():
            partes.append(_p(parrafo.strip(), 10, alinear=4))

    estado = consent.status
    col = (ancho - 10 * mm) / 2
    quien = consent.signed_by_name or "_______________________"
    rel = f" ({consent.signer_relationship})" if consent.signer_relationship else ""
    izquierda = [
        _firma(consent.signature_image, col),
        Table([[""]], colWidths=[col], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, TINTA)]),
        _p(f"{quien}{rel}", 9, True),
        _p(f"C.I. {consent.signer_id_number}" if consent.signer_id_number else "C.I. ___________", 8.5, color=SUAVE),
    ]
    nombre_prof = f"{profesional.first_name} {profesional.last_name}" if profesional else "Profesional tratante"
    derecha = [
        _firma(consent.professional_signature_image, col),
        Table([[""]], colWidths=[col], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, TINTA)]),
        _p(nombre_prof, 9, True),
        _p(f"Registro {profesional.license_number}" if profesional and profesional.license_number else "Registro ___________", 8.5, color=SUAVE),
    ]
    firmas = Table([[izquierda, derecha]], colWidths=[col + 5 * mm, col + 5 * mm])
    firmas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))

    pie = []
    if estado == "firmado" and consent.signed_at:
        canal = "a distancia, desde el dispositivo del paciente" if consent.signed_channel == "remoto" else "de forma presencial"
        texto = f"Firmado el {consent.signed_at:%d/%m/%Y a las %H:%M} UTC, {canal}."
        if consent.signed_ip:
            texto += f" IP {consent.signed_ip}."
        if consent.witness_name:
            texto += f" Testigo: {consent.witness_name}."
        pie.append(_p(texto, 8, color=SUAVE))
    elif consent.voided_at:
        pie.append(_p(f"ANULADO / REVOCADO el {consent.voided_at:%d/%m/%Y}: {consent.void_reason}", 9, True, colors.HexColor("#B3352B")))
    else:
        pie.append(_p("Pendiente de firma.", 8, color=SUAVE))
    if consent.content_hash:
        pie.append(_p(f"Huella del contenido (SHA-256): {consent.content_hash}", 7, color=SUAVE))
    caja = Table([[pie]], colWidths=[ancho], style=[("LINEABOVE", (0, 0), (-1, -1), 0.5, LINEA), ("TOPPADDING", (0, 0), (-1, -1), 6)])

    partes.append(Spacer(0, 10))
    partes.append(KeepTogether([firmas, Spacer(0, 10), caja]))
    doc.build(partes)
    return buf.getvalue()
