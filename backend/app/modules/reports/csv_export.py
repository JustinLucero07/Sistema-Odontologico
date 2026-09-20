"""CSV rendering for the reports.

A report nobody can take out of the screen is half a report: clinics reconcile
against a spreadsheet, and their accountant will not log in. The separator and
the encoding are chosen for that reader, not for a parser.
"""

import csv
import io
from typing import Iterable, Sequence

# Excel in a Spanish locale reads a comma-separated file as one column, so the
# file declares its separator. The BOM is what makes Excel honour UTF-8 and
# stop mangling every accent.
CSV_DELIMITER = ";"
UTF8_BOM = "﻿"


def render_csv(title: str, headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buffer = io.StringIO()
    buffer.write(UTF8_BOM)
    buffer.write(f"sep={CSV_DELIMITER}\n")
    writer = csv.writer(buffer, delimiter=CSV_DELIMITER, lineterminator="\r\n")
    writer.writerow([title])
    writer.writerow([])
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue()


def _decimal(value: object) -> str:
    """Decimals go out with a comma, like the rest of the locale's numbers."""
    return str(value).replace(".", ",")


def financial_csv(report) -> str:
    rows: list[list[object]] = [["Cobrado", _decimal(report.collected), report.payment_count]]
    rows.append(["Facturado en el período", _decimal(report.charged), ""])
    rows.append(["Pendiente de cobro (a hoy)", _decimal(report.outstanding_total), ""])
    rows.append([])
    rows.append(["Por medio de pago", "", ""])
    rows += [[m.label, _decimal(m.amount), m.count] for m in report.by_method]
    if report.by_professional:
        rows.append([])
        rows.append(["Por profesional", "", ""])
        rows += [[p.label, _decimal(p.amount), p.count] for p in report.by_professional]
    rows.append([])
    rows.append(["Antigüedad de la deuda", "", ""])
    rows += [[b.label, _decimal(b.amount), b.count] for b in report.aging]
    if report.voided_count:
        rows.append([])
        rows.append(["Anulados", _decimal(report.voided_total), report.voided_count])

    return render_csv(
        f"Reporte financiero · {report.range.date_from} a {report.range.date_to}",
        ["Concepto", "Importe", "Cantidad"],
        rows,
    )


def clinical_csv(report) -> str:
    rows: list[list[object]] = [["Tratamientos completados", report.treatments_completed, ""]]
    rows.append([])
    rows.append(["Por tratamiento", "Cantidad", "Producción"])
    rows += [[t.label, t.count, _decimal(t.amount)] for t in report.by_treatment]
    rows.append([])
    rows.append(["Por profesional", "Cantidad", "Producción"])
    rows += [[p.label, p.count, _decimal(p.amount)] for p in report.by_professional]
    rows.append([])
    rows.append(["Diagnósticos más frecuentes", "Cantidad", ""])
    rows += [[d.label, d.count, ""] for d in report.top_diagnoses]
    rows.append([])
    b = report.budgets
    rows.append(["Presupuestos aceptados", b.accepted_count, _decimal(b.accepted_amount)])
    rows.append(["Presupuestos rechazados", b.rejected_count, _decimal(b.rejected_amount)])
    rows.append(["Presupuestos sin respuesta", b.pending_count, _decimal(b.pending_amount)])
    rows.append(
        ["Tasa de conversión", "" if b.conversion_rate is None else f"{b.conversion_rate}%", ""]
    )

    return render_csv(
        f"Reporte clínico · {report.range.date_from} a {report.range.date_to}",
        ["Concepto", "Cantidad", "Importe"],
        rows,
    )


def appointment_csv(report) -> str:
    rows: list[list[object]] = [["Total de citas", report.total]]
    rows.append(["Citas concluidas", report.concluded])
    rows.append(["Atendidas", report.attended])
    rows.append(["No asistió", report.no_show])
    rows.append(["Canceladas", report.cancelled])
    rows.append(
        ["Tasa de inasistencia", "" if report.no_show_rate is None else f"{report.no_show_rate}%"]
    )
    rows.append([])
    rows.append(["Por estado", "Cantidad"])
    rows += [[s.label, s.count] for s in report.by_status]
    rows.append([])
    rows.append(["Por profesional", "Cantidad"])
    rows += [[p.label, p.count] for p in report.by_professional]
    rows.append([])
    rows.append(["Por día de la semana", "Cantidad"])
    rows += [[d.label, d.count] for d in report.by_weekday]

    return render_csv(
        f"Reporte de agenda · {report.range.date_from} a {report.range.date_to}",
        ["Concepto", "Cantidad"],
        rows,
    )


def patient_csv(report) -> str:
    rows: list[list[object]] = [["Pacientes nuevos en el período", report.new_patients]]
    rows.append(["Pacientes registrados", report.total_active])
    rows.append(["Atendidos en los últimos 12 meses", report.seen_last_12m])
    rows.append(["Sin atención en 12 meses", report.dormant])
    rows.append([])
    rows.append(["Altas por mes", "Cantidad"])
    rows += [[m.label, m.count] for m in report.by_month]
    rows.append([])
    rows.append(["Por sexo", "Cantidad"])
    rows += [[s.label, s.count] for s in report.by_sex]
    rows.append([])
    rows.append(["Por edad", "Cantidad"])
    rows += [[a.label, a.count] for a in report.by_age_band]

    return render_csv(
        f"Reporte de pacientes · {report.range.date_from} a {report.range.date_to}",
        ["Concepto", "Cantidad"],
        rows,
    )
