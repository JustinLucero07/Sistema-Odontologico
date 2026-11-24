import re
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.appointments.models import Appointment
from app.modules.clinics.models import Clinic
from app.modules.dashboard.service import _clinic_tz
from app.modules.patients.models import Patient
from app.modules.professionals.models import Professional
from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
from app.modules.treatments.models import Treatment

ESTETICOS = re.compile(r"blanque|carilla|dise[nñ]o de sonrisa|est[eé]tic|botox|toxina|[aá]cido hialur|contorne|resina est", re.I)
EDAD_PEDIATRICA = 14


class Cifra(BaseModel):
    codigo: str
    valor: int
    etiqueta: str
    icono: str
    tono: str = "info"
    ruta: str | None = None


class Acceso(BaseModel):
    etiqueta: str
    icono: str
    ruta: str
    query: dict[str, str] = {}


class Fila(BaseModel):
    patient_id: uuid.UUID
    nombre: str
    detalle: str
    hora: datetime | None = None


class Especialidad(BaseModel):
    foco: str
    titulo: str
    subtitulo: str
    cifras: list[Cifra]
    accesos: list[Acceso]
    lista_titulo: str | None = None
    lista: list[Fila] = []
    lista_vacia: str | None = None


def _edad(nac: date, hoy: date) -> int:
    return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))


async def _citas_hoy(db: AsyncSession, clinic_id: uuid.UUID, tz, hoy: date, filtro=None):
    ini = datetime.combine(hoy, time.min, tzinfo=tz)
    q = (
        select(Appointment, Patient, Professional)
        .join(Patient, Patient.id == Appointment.patient_id)
        .join(Professional, Professional.id == Appointment.professional_id)
        .where(
            Appointment.clinic_id == clinic_id,
            Appointment.starts_at >= ini,
            Appointment.starts_at < ini + timedelta(days=1),
            Appointment.status.notin_(("cancelada", "no_asistio")),
            Patient.deleted_at.is_(None),
        )
        .order_by(Appointment.starts_at)
    )
    if filtro is not None:
        q = q.where(filtro)
    return (await db.execute(q)).all()


async def _ortodoncia(db, user, clinic, tz, hoy) -> Especialidad:
    from app.modules.orthodontics.models import OrthoCase, OrthoControl
    from app.modules.orthodontics.service import code_for

    cid = clinic.id
    activos = await db.scalar(
        select(func.count()).select_from(OrthoCase).where(OrthoCase.clinic_id == cid, OrthoCase.status.in_(("activo", "retencion")))
    ) or 0
    atrasados = await db.scalar(
        select(func.count(func.distinct(OrthoCase.id)))
        .select_from(OrthoCase)
        .join(OrthoControl, OrthoControl.case_id == OrthoCase.id)
        .where(
            OrthoCase.clinic_id == cid,
            OrthoCase.status.in_(("activo", "retencion", "pausa")),
            OrthoControl.planned_on < hoy,
            OrthoControl.attended_on.is_(None),
        )
    ) or 0
    semana = await db.scalar(
        select(func.count())
        .select_from(OrthoControl)
        .join(OrthoCase, OrthoCase.id == OrthoControl.case_id)
        .where(
            OrthoCase.clinic_id == cid,
            OrthoControl.attended_on.is_(None),
            OrthoControl.planned_on >= hoy,
            OrthoControl.planned_on < hoy + timedelta(days=7),
        )
    ) or 0
    casos = {
        pid: (numero, estado)
        for pid, numero, estado in (
            await db.execute(
                select(OrthoCase.patient_id, OrthoCase.number, OrthoCase.status).where(
                    OrthoCase.clinic_id == cid, OrthoCase.status.in_(("activo", "retencion", "pausa"))
                )
            )
        ).all()
    }
    filas = await _citas_hoy(db, cid, tz, hoy, Appointment.patient_id.in_(list(casos) or [uuid.uuid4()]))
    return Especialidad(
        foco="ortodoncia",
        titulo="Tu día de ortodoncia",
        subtitulo="Controles, atrasos y fichas activas de un vistazo.",
        cifras=[
            Cifra(codigo="hoy", valor=len(filas), etiqueta="controles hoy", icono="event_available", ruta="/agenda"),
            Cifra(codigo="semana", valor=semana, etiqueta="controles esta semana", icono="date_range", ruta="/orthodontics"),
            Cifra(codigo="atrasados", valor=atrasados, etiqueta="con control atrasado", icono="schedule",
                  tono="alerta" if atrasados else "ok", ruta="/orthodontics"),
            Cifra(codigo="activos", valor=activos, etiqueta="fichas activas", icono="sentiment_very_satisfied", ruta="/orthodontics"),
        ],
        accesos=[
            Acceso(etiqueta="Lista de ortodoncia", icono="format_list_bulleted", ruta="/orthodontics"),
            Acceso(etiqueta="Agendar control", icono="event", ruta="/agenda", query={"nueva": "1"}),
            Acceso(etiqueta="A quién llamar hoy", icono="call", ruta="/opportunities"),
        ],
        lista_titulo="Pacientes de ortodoncia que vienen hoy",
        lista=[
            Fila(
                patient_id=p.id, nombre=f"{p.first_name} {p.last_name}", hora=a.starts_at,
                detalle=f"{code_for(casos[p.id][0])} · {pr.first_name} {pr.last_name}",
            )
            for a, p, pr in filas
        ],
        lista_vacia="Hoy no hay controles de ortodoncia agendados.",
    )


async def _estetica(db, user, clinic, tz, hoy) -> Especialidad:
    from app.modules.imaging.comparisons import ImageComparison

    cid = clinic.id
    inicio_mes = datetime.combine(hoy.replace(day=1), time.min, tzinfo=tz)
    comps_mes = await db.scalar(
        select(func.count()).select_from(ImageComparison).where(
            ImageComparison.clinic_id == cid, ImageComparison.created_at >= inicio_mes
        )
    ) or 0
    para_redes = await db.scalar(
        select(func.count()).select_from(ImageComparison).where(
            ImageComparison.clinic_id == cid, ImageComparison.share_consent.is_(True)
        )
    ) or 0
    items = (
        await db.execute(
            select(TreatmentPlan.patient_id, Treatment.name, TreatmentPlanItem.status)
            .join(TreatmentPlanItem, TreatmentPlanItem.plan_id == TreatmentPlan.id)
            .join(Treatment, Treatment.id == TreatmentPlanItem.treatment_id)
            .where(
                TreatmentPlan.clinic_id == cid,
                TreatmentPlan.cancelled_at.is_(None),
                TreatmentPlanItem.status.in_(("propuesto", "aprobado", "en_progreso")),
            )
        )
    ).all()
    esteticos = [(pid, n, s) for pid, n, s in items if ESTETICOS.search(n or "")]
    propuestos = sum(1 for _, _, s in esteticos if s == "propuesto")
    en_curso = len(esteticos) - propuestos
    filas = await _citas_hoy(db, cid, tz, hoy)
    tratamientos: dict[uuid.UUID, str] = {}
    for pid, n, _ in esteticos:
        tratamientos.setdefault(pid, n)
    return Especialidad(
        foco="estetica",
        titulo="Tu día de estética dental",
        subtitulo="Lo que vende tu consulta: resultados, propuestas y fotos para mostrar.",
        cifras=[
            Cifra(codigo="propuestos", valor=propuestos, etiqueta="propuestas estéticas sin aceptar", icono="request_quote",
                  tono="dinero" if propuestos else "ok", ruta="/opportunities"),
            Cifra(codigo="curso", valor=en_curso, etiqueta="tratamientos estéticos en curso", icono="auto_awesome"),
            Cifra(codigo="comparaciones", valor=comps_mes, etiqueta="antes y después este mes", icono="compare"),
            Cifra(codigo="redes", valor=para_redes, etiqueta="autorizados para redes", icono="share"),
        ],
        accesos=[
            Acceso(etiqueta="Pacientes", icono="groups", ruta="/patients"),
            Acceso(etiqueta="Oportunidades", icono="tips_and_updates", ruta="/opportunities"),
            Acceso(etiqueta="Nueva cita", icono="event", ruta="/agenda", query={"nueva": "1"}),
        ],
        lista_titulo="Hoy vienen",
        lista=[
            Fila(
                patient_id=p.id, nombre=f"{p.first_name} {p.last_name}", hora=a.starts_at,
                detalle=f"Pendiente: {tratamientos[p.id]}" if p.id in tratamientos else f"{pr.first_name} {pr.last_name}",
            )
            for a, p, pr in filas
        ],
        lista_vacia="Hoy no hay citas agendadas.",
    )


async def _pediatria(db, user, clinic, tz, hoy) -> Especialidad:
    cid = clinic.id
    try:
        limite = hoy.replace(year=hoy.year - EDAD_PEDIATRICA)
    except ValueError:
        limite = date(hoy.year - EDAD_PEDIATRICA, 3, 1)
    menores = and_(Patient.birth_date.is_not(None), Patient.birth_date > limite)
    total = await db.scalar(
        select(func.count()).select_from(Patient).where(Patient.clinic_id == cid, Patient.deleted_at.is_(None), menores)
    ) or 0
    inicio_mes = datetime.combine(hoy.replace(day=1), time.min, tzinfo=tz)
    atendidos_mes = await db.scalar(
        select(func.count(func.distinct(Appointment.patient_id)))
        .select_from(Appointment)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.clinic_id == cid, Appointment.status == "atendida", Appointment.starts_at >= inicio_mes, menores)
    ) or 0
    ultima = (
        select(Appointment.patient_id, func.max(Appointment.starts_at).label("u"))
        .where(Appointment.clinic_id == cid, Appointment.status == "atendida")
        .group_by(Appointment.patient_id)
        .subquery()
    )
    sin_control = await db.scalar(
        select(func.count())
        .select_from(Patient)
        .join(ultima, ultima.c.patient_id == Patient.id)
        .where(Patient.clinic_id == cid, Patient.deleted_at.is_(None), menores,
               ultima.c.u < datetime.now(timezone.utc) - timedelta(days=183))
    ) or 0
    cumple = 0
    for (nac,) in (
        await db.execute(select(Patient.birth_date).where(Patient.clinic_id == cid, Patient.deleted_at.is_(None), menores))
    ).all():
        try:
            este = nac.replace(year=hoy.year)
        except ValueError:
            este = date(hoy.year, 3, 1)
        if 0 <= (este - hoy).days <= 7:
            cumple += 1
    filas = await _citas_hoy(db, cid, tz, hoy, menores)
    return Especialidad(
        foco="pediatria",
        titulo="Tu día de odontopediatría",
        subtitulo=f"Pacientes menores de {EDAD_PEDIATRICA} años: controles, cumpleaños y quién viene hoy.",
        cifras=[
            Cifra(codigo="hoy", valor=len(filas), etiqueta="niños hoy", icono="child_care", ruta="/agenda"),
            Cifra(codigo="sin_control", valor=sin_control, etiqueta="sin control en 6 meses", icono="person_search",
                  tono="alerta" if sin_control else "ok", ruta="/opportunities"),
            Cifra(codigo="mes", valor=atendidos_mes, etiqueta="niños atendidos este mes", icono="mood"),
            Cifra(codigo="cumple", valor=cumple, etiqueta="cumplen años esta semana", icono="cake", ruta="/opportunities"),
            Cifra(codigo="total", valor=total, etiqueta="pacientes niños", icono="groups", ruta="/patients"),
        ],
        accesos=[
            Acceso(etiqueta="Pacientes", icono="groups", ruta="/patients"),
            Acceso(etiqueta="Agendar control", icono="event", ruta="/agenda", query={"nueva": "1"}),
            Acceso(etiqueta="A quién llamar hoy", icono="call", ruta="/opportunities"),
        ],
        lista_titulo="Niños que vienen hoy",
        lista=[
            Fila(
                patient_id=p.id, nombre=f"{p.first_name} {p.last_name}", hora=a.starts_at,
                detalle=f"{_edad(p.birth_date, hoy)} años · {pr.first_name} {pr.last_name}",
            )
            for a, p, pr in filas
        ],
        lista_vacia="Hoy no hay niños agendados.",
    )


ARMADORES = {"ortodoncia": _ortodoncia, "estetica": _estetica, "pediatria": _pediatria}

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/specialty", response_model=Especialidad | None)
async def get_especialidad(db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    clinic = await db.get(Clinic, current_user.clinic_id)
    foco = clinic.specialty_focus or "general"
    if foco not in ARMADORES or not current_user.has_permission("appointments:read"):
        return None
    if foco == "ortodoncia" and not (clinic.orthodontics_enabled and current_user.has_permission("orthodontics:read")):
        return None
    tz = await _clinic_tz(db, clinic.id)
    hoy = datetime.now(timezone.utc).astimezone(tz).date()
    return await ARMADORES[foco](db, current_user, clinic, tz, hoy)
