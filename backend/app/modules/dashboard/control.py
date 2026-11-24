import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.appointments.models import Appointment
from app.modules.clinics.models import Clinic
from app.modules.dashboard.service import _clinic_tz
from app.modules.patients.models import Patient
from app.modules.payments.models import Payment

ZERO = Decimal("0.00")


class DiaMonto(BaseModel):
    date: date
    amount: Decimal


class ControlOut(BaseModel):
    today: date
    # Meta del mes
    monthly_goal: Decimal | None
    collected_month: Decimal | None
    collected_previous_same_period: Decimal | None
    goal_progress: float | None  # 0..1+ (puede pasar de 1)
    projection_month: Decimal | None
    workdays_total: int
    workdays_elapsed: int
    workdays_left: int
    needed_per_workday: Decimal | None
    # Hoy
    collected_today: Decimal | None
    payments_today: int | None
    appointments_today: int
    appointments_confirmed: int
    appointments_attended: int
    appointments_pending_confirm: int
    no_shows_today: int
    # Mes
    no_shows_month: int
    new_patients_month: int
    daily_income: list[DiaMonto] | None  # últimos 30 días
    ortho_overdue: int | None
    receipts_pending: int | None = None


class GoalIn(BaseModel):
    monthly_goal: Decimal | None = Field(default=None, ge=0, le=Decimal("10000000"))


def _laborables(desde: date, hasta: date, dias: str) -> int:
    if hasta < desde:
        return 0
    n = 0
    d = desde
    while d <= hasta:
        if str(d.isoweekday()) in dias:
            n += 1
        d += timedelta(days=1)
    return n


async def build_control(db: AsyncSession, current_user: CurrentUser) -> ControlOut:
    clinic_id = current_user.clinic_id
    puede = lambda p: current_user.is_superadmin or p in current_user.permissions  # noqa: E731
    clinic = await db.get(Clinic, clinic_id)
    tz = await _clinic_tz(db, clinic_id)
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(tz).date()
    inicio_mes = hoy.replace(day=1)
    fin_mes = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])
    dias = clinic.work_days or "123456"

    total_lab = _laborables(inicio_mes, fin_mes, dias)
    transcurridos = _laborables(inicio_mes, hoy, dias)
    # Hoy todavía cuenta como día para cobrar.
    quedan = _laborables(hoy, fin_mes, dias)

    # Citas de hoy y del mes (en la zona horaria de la clínica).
    dia_local = func.date(func.timezone(clinic.timezone or "UTC", Appointment.starts_at))
    filas = (
        await db.execute(
            select(Appointment.status, func.count()).where(
                Appointment.clinic_id == clinic_id, dia_local == hoy
            ).group_by(Appointment.status)
        )
    ).all()
    por_estado = {s: n for s, n in filas}
    citas_hoy = sum(n for s, n in por_estado.items() if s != "cancelada")
    no_mes = await db.scalar(
        select(func.count()).select_from(Appointment).where(
            Appointment.clinic_id == clinic_id, Appointment.status == "no_asistio",
            dia_local >= inicio_mes, dia_local <= hoy,
        )
    )
    nuevos = await db.scalar(
        select(func.count()).select_from(Patient).where(
            Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None),
            Patient.created_at >= datetime.combine(inicio_mes, datetime.min.time(), tzinfo=tz),
        )
    )

    meta = cobrado = previo = progreso = proyeccion = por_dia = cobrado_hoy = None
    pagos_hoy = None
    diario = None
    if puede("payments:read"):
        async def suma(a: date, b: date) -> Decimal:
            v = await db.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.clinic_id == clinic_id, Payment.voided_at.is_(None),
                    Payment.received_on >= a, Payment.received_on <= b,
                )
            )
            return Decimal(v or 0).quantize(ZERO)

        cobrado = await suma(inicio_mes, hoy)
        cobrado_hoy = await suma(hoy, hoy)
        pagos_hoy = await db.scalar(
            select(func.count()).select_from(Payment).where(
                Payment.clinic_id == clinic_id, Payment.voided_at.is_(None), Payment.received_on == hoy
            )
        )
        fin_prev = inicio_mes - timedelta(days=1)
        ini_prev = fin_prev.replace(day=1)
        previo = await suma(ini_prev, ini_prev.replace(day=min(hoy.day, fin_prev.day)))
        meta = clinic.monthly_goal
        # Proyección al ritmo de los días laborables ya pasados.
        if transcurridos > 0:
            proyeccion = (cobrado / transcurridos * total_lab).quantize(ZERO)
        if meta and meta > 0:
            progreso = float(cobrado / meta)
            falta = max(meta - cobrado, ZERO)
            por_dia = (falta / quedan).quantize(ZERO) if quedan else falta
        desde = hoy - timedelta(days=29)
        filas = (
            await db.execute(
                select(Payment.received_on, func.sum(Payment.amount)).where(
                    Payment.clinic_id == clinic_id, Payment.voided_at.is_(None),
                    Payment.received_on >= desde, Payment.received_on <= hoy,
                ).group_by(Payment.received_on)
            )
        ).all()
        mapa = {d: Decimal(v).quantize(ZERO) for d, v in filas}
        diario = [DiaMonto(date=desde + timedelta(days=i), amount=mapa.get(desde + timedelta(days=i), ZERO)) for i in range(30)]

    orto = None
    if clinic.orthodontics_enabled and puede("orthodontics:read"):
        from app.modules.orthodontics.models import OrthoCase, OrthoControl

        orto = await db.scalar(
            select(func.count(func.distinct(OrthoCase.id)))
            .select_from(OrthoCase)
            .join(OrthoControl, OrthoControl.case_id == OrthoCase.id)
            .where(
                OrthoCase.clinic_id == clinic_id,
                OrthoCase.status.in_(["activo", "retencion", "pausa"]),
                OrthoControl.planned_on < hoy,
                OrthoControl.attended_on.is_(None),
            )
        )

    comprobantes = None
    if puede("payments:read"):
        from app.modules.portal.models import PortalReceipt

        comprobantes = await db.scalar(
            select(func.count()).select_from(PortalReceipt).where(
                PortalReceipt.clinic_id == clinic_id, PortalReceipt.status == "pendiente"
            )
        )

    return ControlOut(
        today=hoy,
        monthly_goal=meta,
        collected_month=cobrado,
        collected_previous_same_period=previo,
        goal_progress=progreso,
        projection_month=proyeccion,
        workdays_total=total_lab,
        workdays_elapsed=transcurridos,
        workdays_left=quedan,
        needed_per_workday=por_dia,
        collected_today=cobrado_hoy,
        payments_today=pagos_hoy,
        appointments_today=citas_hoy,
        appointments_confirmed=por_estado.get("confirmada", 0),
        appointments_attended=por_estado.get("atendida", 0),
        appointments_pending_confirm=por_estado.get("programada", 0),
        no_shows_today=por_estado.get("no_asistio", 0),
        no_shows_month=no_mes or 0,
        new_patients_month=nuevos or 0,
        daily_income=diario,
        ortho_overdue=orto,
        receipts_pending=comprobantes,
    )


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/control", response_model=ControlOut)
async def get_control(db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return await build_control(db, current_user)


@router.put("/goal", response_model=ControlOut)
async def put_goal(payload: GoalIn, db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """La meta del mes la define quien administra la configuración."""
    if not (current_user.is_superadmin or "settings:manage" in current_user.permissions):
        raise HTTPException(status_code=403, detail="Solo quien administra la configuración puede cambiar la meta.")
    clinic = await db.get(Clinic, current_user.clinic_id)
    antes = str(clinic.monthly_goal) if clinic.monthly_goal is not None else None
    clinic.monthly_goal = payload.monthly_goal.quantize(ZERO) if payload.monthly_goal else None
    await record_audit(
        db, clinic_id=clinic.id, user_id=current_user.id, action="update", entity_type="clinic",
        entity_id=str(clinic.id), before={"monthly_goal": antes}, after={"monthly_goal": str(clinic.monthly_goal)},
    )
    await db.commit()
    return await build_control(db, current_user)
