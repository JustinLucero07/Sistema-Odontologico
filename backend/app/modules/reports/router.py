from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.reports import csv_export, service
from app.modules.reports.schemas import (
    AppointmentReport,
    ClinicalReport,
    FinancialReport,
    PatientReport,
    ReportSummary,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# A range longer than this is almost always a mistyped year, and it makes the
# in-Python grouping slow enough to notice.
MAX_RANGE_DAYS = 400


def _range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    """Defaults to the last 30 days, and refuses a backwards or absurd range
    rather than returning an empty report that looks like bad business."""
    to = date_to or date.today()
    frm = date_from or (to - timedelta(days=29))
    if frm > to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha inicial no puede ser posterior a la final",
        )
    if (to - frm).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rango no puede superar {MAX_RANGE_DAYS} días",
        )
    return frm, to


def _csv_response(body: str, name: str, frm: date, to: date) -> Response:
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}-{frm}-{to}.csv"',
        },
    )


@router.get("/summary", response_model=ReportSummary)
async def get_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.summary(db, current_user.clinic_id, frm, to)


@router.get("/financial", response_model=FinancialReport)
async def get_financial(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.financial_report(db, current_user.clinic_id, frm, to)


@router.get("/financial.csv")
async def get_financial_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    report = await service.financial_report(db, current_user.clinic_id, frm, to)
    return _csv_response(csv_export.financial_csv(report), "financiero", frm, to)


@router.get("/clinical", response_model=ClinicalReport)
async def get_clinical(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.clinical_report(db, current_user.clinic_id, frm, to)


@router.get("/clinical.csv")
async def get_clinical_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    report = await service.clinical_report(db, current_user.clinic_id, frm, to)
    return _csv_response(csv_export.clinical_csv(report), "clinico", frm, to)


@router.get("/appointments", response_model=AppointmentReport)
async def get_appointments(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.appointment_report(db, current_user.clinic_id, frm, to)


@router.get("/appointments.csv")
async def get_appointments_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    report = await service.appointment_report(db, current_user.clinic_id, frm, to)
    return _csv_response(csv_export.appointment_csv(report), "agenda", frm, to)


@router.get("/patients", response_model=PatientReport)
async def get_patients(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.patient_report(db, current_user.clinic_id, frm, to)


@router.get("/patients.csv")
async def get_patients_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    frm, to = _range(date_from, date_to)
    report = await service.patient_report(db, current_user.clinic_id, frm, to)
    return _csv_response(csv_export.patient_csv(report), "pacientes", frm, to)
