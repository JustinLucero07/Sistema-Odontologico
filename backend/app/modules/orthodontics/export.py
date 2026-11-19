"""Panel de pagos de una ficha de ortodoncia, para imprimir (PDF) o abrir en
Excel (CSV con separador «;» y BOM, que Excel en español abre directo)."""

import csv
import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.orthodontics.constants import CASE_STATUSES, DOC_FIELDS, DOC_STATUSES, TAD_OPTIONS
from app.modules.orthodontics.schemas import CaseDetail

_ESTADO = dict(CASE_STATUSES)
_TAD = dict(TAD_OPTIONS)
_DOC = dict(DOC_STATUSES)
_CUOTA = {"pendiente": "Pendiente", "parcial": "Parcial", "pagada": "Pagada", "vencida": "Vencida", "sin_valor": "—"}


def _f(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _m(v: Decimal) -> str:
    return f"${v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def to_csv(case: CaseDetail) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    p = case.patient
    w.writerow(["Ficha", case.code, "Paciente", f"{p.first_name} {p.last_name}", "Cédula", p.national_id or ""])
    w.writerow(["Valor del tratamiento", f"{case.agreed_total:.2f}", "Recibido", f"{case.paid:.2f}",
                "Saldo", f"{case.balance:.2f}"])
    w.writerow([])
    w.writerow(["Cuota", "Fecha planificada", "Asistió", "Planificación", "Arcos", "Elásticos", "TADs",
                "Vencimiento", "Valor", "Abonado", "Saldo", "Estado"])
    for c in case.controls:
        w.writerow([
            f"{c.number:02d}", _f(c.planned_on), _f(c.attended_on), c.planning or "", c.arches or "",
            c.elastics or "", c.tads or "", _f(c.due_on), f"{c.amount:.2f}", f"{c.paid:.2f}",
            f"{c.balance:.2f}", _CUOTA.get(c.status, c.status),
        ])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def to_pdf(case: CaseDetail, clinic_name: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"Ortodoncia {case.code}",
    )
    est = getSampleStyleSheet()
    chico = ParagraphStyle("chico", parent=est["Normal"], fontSize=7.5, leading=9)
    normal = ParagraphStyle("n", parent=est["Normal"], fontSize=9, leading=12)
    titulo = ParagraphStyle("t", parent=est["Heading2"], fontSize=14, spaceAfter=2)
    p = case.patient
    partes = [
        Paragraph(clinic_name, normal),
        Paragraph(f"Ortodoncia {case.code} · Panel de pagos", titulo),
        Paragraph(
            f"<b>Paciente:</b> {p.first_name} {p.last_name} &nbsp; <b>Cédula:</b> {p.national_id or '—'} &nbsp; "
            f"<b>Estado:</b> {_ESTADO.get(case.status, case.status)} &nbsp; "
            f"<b>TAD:</b> {_TAD.get(case.has_tad, case.has_tad)} &nbsp; "
            f"<b>Profesional:</b> {case.professional_name or '—'}",
            normal,
        ),
        Paragraph(
            f"<b>Valor del tratamiento:</b> {_m(case.agreed_total)} &nbsp; <b>Recibido:</b> {_m(case.paid)} &nbsp; "
            f"<b>Saldo:</b> {_m(case.balance)}",
            normal,
        ),
        Paragraph(
            "<b>Documentación:</b> " + " · ".join(f"{et}: {_DOC.get(getattr(case, f), '')}" for f, et in DOC_FIELDS),
            normal,
        ),
        Spacer(1, 6),
    ]
    filas = [["Cuota", "F. planif.", "Asistió", "Planificación", "Arcos", "Elásticos", "TADs",
              "Vence", "Valor", "Abonado", "Saldo", "Estado"]]
    for c in case.controls:
        filas.append([
            f"{c.number:02d}", _f(c.planned_on), _f(c.attended_on),
            Paragraph(c.planning or "", chico), Paragraph(c.arches or "", chico),
            Paragraph(c.elastics or "", chico), Paragraph(c.tads or "", chico),
            _f(c.due_on), _m(c.amount), _m(c.paid), _m(c.balance), _CUOTA.get(c.status, c.status),
        ])
    if len(filas) == 1:
        filas.append(["", "", "", Paragraph("Sin cuotas registradas", chico), "", "", "", "", "", "", "", ""])
    t = Table(filas, repeatRows=1, colWidths=[12 * mm, 19 * mm, 19 * mm, 52 * mm, 34 * mm, 30 * mm, 28 * mm,
                                               19 * mm, 18 * mm, 18 * mm, 18 * mm, 16 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d7f76")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (8, 1), (10, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c9d3d1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f6")]),
    ]))
    partes.append(t)
    doc.build(partes)
    return buf.getvalue()
