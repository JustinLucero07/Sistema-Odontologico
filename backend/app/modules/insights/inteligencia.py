import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.appointments.constants import DEFAULT_REMINDER_OFFSETS_MINUTES
from app.modules.appointments.models import Appointment
from app.modules.clinics.models import Clinic
from app.modules.dashboard.service import _clinic_tz
from app.modules.insights.service import ACTIVE_STATUSES, DAY_END, DAY_START, RECALL_MONTHS, _revoked
from app.modules.patients.models import Patient
from app.modules.professionals.models import Professional
from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
from app.modules.treatments.models import Treatment

VENTANA = 10
OFFSETS_POR_RIESGO = {
    "alto": [72 * 60, 24 * 60, 120],
    "medio": [48 * 60, 24 * 60, 120],
}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos"]
HUECO_MINIMO = 30


@dataclass
class Riesgo:
    nivel: str
    faltas: int
    total: int
    dia: int | None = None
    franja: str | None = None
    profesional_id: uuid.UUID | None = None

    @property
    def texto(self) -> str:
        if self.nivel == "nuevo":
            return "Sin historial de citas"
        if self.faltas == 0:
            return f"Asistió a sus últimas {self.total} citas" if self.total > 1 else "Asistió a su única cita"
        if self.nivel == "bajo":
            return f"Asistió a {self.total - self.faltas} de sus últimas {self.total} citas"
        return f"Faltó a {self.faltas} de sus últimas {self.total} citas"


def _franja(h: int) -> str:
    return "mañana" if h < 12 else "tarde" if h < 17 else "noche"


def nivel(faltas: int, total: int) -> str:
    if total == 0:
        return "nuevo"
    tasa = faltas / total
    if faltas >= 2 and tasa >= 0.25:
        return "alto"
    if faltas >= 1 and tasa >= 0.15:
        return "medio"
    return "bajo"


async def riesgos(db: AsyncSession, clinic_id: uuid.UUID, ids: set[uuid.UUID], tz=None) -> dict[uuid.UUID, Riesgo]:
    if not ids:
        return {}
    tz = tz or await _clinic_tz(db, clinic_id)
    filas = (
        await db.execute(
            select(Appointment.patient_id, Appointment.status, Appointment.starts_at, Appointment.professional_id)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.patient_id.in_(ids),
                Appointment.status.in_(("atendida", "no_asistio")),
                Appointment.starts_at < datetime.now(timezone.utc),
            )
            .order_by(Appointment.starts_at.desc())
        )
    ).all()
    por: dict[uuid.UUID, list] = defaultdict(list)
    for f in filas:
        if len(por[f.patient_id]) < VENTANA:
            por[f.patient_id].append(f)
    out = {}
    for pid in ids:
        h = por.get(pid, [])
        faltas = sum(1 for f in h if f.status == "no_asistio")
        r = Riesgo(nivel(faltas, len(h)), faltas, len(h))
        vino = [f for f in h if f.status == "atendida"]
        if len(vino) >= 2:
            locales = [f.starts_at.astimezone(tz) for f in vino]
            dia, n = Counter(d.weekday() for d in locales).most_common(1)[0]
            r.dia = dia if n >= 2 else None
            franja, n = Counter(_franja(d.hour) for d in locales).most_common(1)[0]
            r.franja = franja if n >= 2 else None
            prof, n = Counter(f.professional_id for f in vino).most_common(1)[0]
            r.profesional_id = prof if n >= 2 else None
        out[pid] = r
    return out


async def offsets_recordatorio(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[int]:
    r = (await riesgos(db, clinic_id, {patient_id})).get(patient_id)
    return OFFSETS_POR_RIESGO.get(r.nivel if r else "", DEFAULT_REMINDER_OFFSETS_MINUTES)


class RiesgoOut(BaseModel):
    patient_id: uuid.UUID
    nivel: str
    faltas: int
    total: int
    texto: str


class Hueco(BaseModel):
    professional_id: uuid.UUID
    professional_name: str
    starts_at: datetime
    ends_at: datetime
    minutos: int


class Sugerencia(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    phone: str | None
    whatsapp: str | None
    motivo: str
    detalle: str
    razones: list[str]
    riesgo: str
    puntaje: int
    hueco: Hueco | None
    mensaje: str


class LlamarHoy(BaseModel):
    huecos: list[Hueco]
    minutos_libres: int
    sugerencias: list[Sugerencia]


@dataclass
class _Candidato:
    paciente: Patient
    motivo: str
    peso: int
    detalles: list[str] = field(default_factory=list)


def _cuando(inicio: datetime, hoy: date) -> str:
    d = inicio.date()
    dia = "hoy" if d == hoy else "mañana" if d == hoy + timedelta(days=1) else f"el {DIAS[d.weekday()].rstrip('s')} {d.day}"
    return f"{dia} a las {inicio:%H:%M}"


async def huecos_libres(db: AsyncSession, clinic_id: uuid.UUID, tz, ahora: datetime) -> list[Hueco]:
    clinic = await db.get(Clinic, clinic_id)
    hora = lambda txt, defecto: time(*map(int, txt.split(":"))) if txt else defecto
    abre, cierra = hora(clinic.opens_at, DAY_START), hora(clinic.closes_at, DAY_END)
    laborables = set(clinic.work_days or "123456")
    hoy = ahora.astimezone(tz).date()
    dias: list[date] = []
    d = hoy
    while len(dias) < 2 and (d - hoy).days < 8:
        if str(d.isoweekday()) in laborables:
            dias.append(d)
        d += timedelta(days=1)
    if not dias:
        return []
    profs = (
        await db.execute(select(Professional).where(Professional.clinic_id == clinic_id, Professional.is_active.is_(True)))
    ).scalars().all()
    inicio = datetime.combine(dias[0], time.min, tzinfo=tz)
    fin = datetime.combine(dias[-1], time.max, tzinfo=tz)
    ocupado: dict[uuid.UUID, list[tuple[datetime, datetime]]] = defaultdict(list)
    for pid, s, e in (
        await db.execute(
            select(Appointment.professional_id, Appointment.starts_at, Appointment.ends_at).where(
                Appointment.clinic_id == clinic_id,
                Appointment.starts_at < fin,
                Appointment.ends_at > inicio,
                Appointment.status.notin_(("cancelada", "no_asistio")),
            )
        )
    ).all():
        ocupado[pid].append((s.astimezone(tz), e.astimezone(tz)))

    desde_ya = ahora.astimezone(tz)
    desde_ya = desde_ya.replace(second=0, microsecond=0) + timedelta(minutes=(15 - desde_ya.minute % 15) % 15 or 15)
    out: list[Hueco] = []
    for p in profs:
        for dia in dias:
            cursor = max(datetime.combine(dia, abre, tzinfo=tz), desde_ya)
            cierre = datetime.combine(dia, cierra, tzinfo=tz)
            del_dia = sorted((s, e) for s, e in ocupado[p.id] if s < cierre and e > cursor)
            for s, e in del_dia + [(cierre, cierre)]:
                if s - cursor >= timedelta(minutes=HUECO_MINIMO):
                    out.append(Hueco(
                        professional_id=p.id, professional_name=f"{p.first_name} {p.last_name}",
                        starts_at=cursor.astimezone(timezone.utc), ends_at=s.astimezone(timezone.utc),
                        minutos=int((s - cursor).total_seconds() // 60),
                    ))
                cursor = max(cursor, e)
    out.sort(key=lambda h: (h.starts_at, h.professional_name))
    return out


async def llamar_hoy(db: AsyncSession, user: CurrentUser) -> LlamarHoy:
    clinic_id = user.clinic_id
    tz = await _clinic_tz(db, clinic_id)
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(tz).date()
    clinic = await db.get(Clinic, clinic_id)
    huecos = await huecos_libres(db, clinic_id, tz, ahora)

    pacientes = {
        p.id: p
        for p in (
            await db.execute(select(Patient).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)))
        ).scalars().all()
    }
    con_cita = set(
        (
            await db.execute(
                select(Appointment.patient_id).where(
                    Appointment.clinic_id == clinic_id,
                    Appointment.starts_at >= ahora,
                    Appointment.status.in_(ACTIVE_STATUSES),
                )
            )
        ).scalars().all()
    )
    cand: dict[uuid.UUID, _Candidato] = {}

    def sumar(pid, motivo, peso, detalle):
        p = pacientes.get(pid)
        if p is None or pid in con_cita:
            return
        c = cand.get(pid)
        if c is None:
            cand[pid] = _Candidato(p, motivo, peso, [detalle])
            return
        if detalle not in c.detalles:
            c.detalles.append(detalle)
        if peso > c.peso:
            c.motivo, c.peso = motivo, peso

    if user.has_permission("orthodontics:read") and clinic.orthodontics_enabled:
        from app.modules.orthodontics.models import OrthoCase, OrthoControl

        for pid, planeado in (
            await db.execute(
                select(OrthoCase.patient_id, OrthoControl.planned_on)
                .join(OrthoControl, OrthoControl.case_id == OrthoCase.id)
                .where(
                    OrthoCase.clinic_id == clinic_id,
                    OrthoCase.status.in_(["activo", "retencion", "pausa"]),
                    OrthoControl.planned_on < hoy + timedelta(days=3),
                    OrthoControl.attended_on.is_(None),
                )
                .order_by(OrthoControl.planned_on)
            )
        ).all():
            texto = (
                f"Control de ortodoncia atrasado desde el {planeado:%d/%m}"
                if planeado < hoy else f"Control de ortodoncia previsto para el {planeado:%d/%m}"
            )
            sumar(pid, "ortodoncia", 40, texto)

    hace_30 = ahora - timedelta(days=30)
    recientes = (
        await db.execute(
            select(Appointment.patient_id, Appointment.status, Appointment.starts_at)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.status.in_(("cancelada", "no_asistio")),
                Appointment.starts_at >= hace_30,
                Appointment.starts_at < ahora + timedelta(days=30),
            )
            .order_by(Appointment.starts_at.desc())
        )
    ).all()
    vino_despues = {
        pid: ult
        for pid, ult in (
            await db.execute(
                select(Appointment.patient_id, Appointment.starts_at).where(
                    Appointment.clinic_id == clinic_id, Appointment.status == "atendida", Appointment.starts_at >= hace_30
                )
            )
        ).all()
    }
    for pid, estado, cuando in recientes:
        if pid in vino_despues and vino_despues[pid] > cuando:
            continue
        local = cuando.astimezone(tz)
        verbo = "Canceló" if estado == "cancelada" else "Faltó a"
        sumar(pid, "reagendar", 35, f"{verbo} su cita del {local:%d/%m} y no ha reagendado")

    for pid, nombre in (
        await db.execute(
            select(TreatmentPlan.patient_id, Treatment.name)
            .join(TreatmentPlanItem, TreatmentPlanItem.plan_id == TreatmentPlan.id)
            .join(Treatment, Treatment.id == TreatmentPlanItem.treatment_id)
            .where(TreatmentPlan.clinic_id == clinic_id, TreatmentPlanItem.status.in_(("aprobado", "en_progreso")))
        )
    ).all():
        c = cand.get(pid)
        previo = next((d for d in (c.detalles if c else []) if d.startswith("Tratamiento pendiente")), None)
        if previo and c:
            if nombre not in previo:
                c.detalles[c.detalles.index(previo)] = f"{previo}, {nombre}"
            continue
        sumar(pid, "tratamiento", 30, f"Tratamiento pendiente: {nombre}")

    for pid, ultima in (
        await db.execute(
            select(Appointment.patient_id, func.max(Appointment.starts_at))
            .where(Appointment.clinic_id == clinic_id, Appointment.status == "atendida")
            .group_by(Appointment.patient_id)
        )
    ).all():
        d = ultima.astimezone(tz).date()
        meses = (hoy.year - d.year) * 12 + hoy.month - d.month
        if meses >= RECALL_MONTHS:
            sumar(pid, "control", 15, f"Última visita hace {meses} meses")

    bloqueados = await _revoked(db, clinic_id, set(cand))
    for pid in bloqueados:
        cand.pop(pid, None)
    rs = await riesgos(db, clinic_id, set(cand), tz)

    sugerencias: list[Sugerencia] = []
    for pid, c in cand.items():
        r = rs[pid]
        puntaje = c.peso
        razones = list(c.detalles)
        if r.nivel == "bajo" and r.total >= 2:
            puntaje += 15
            razones.append(r.texto)
        elif r.nivel == "medio":
            puntaje -= 10
            razones.append(r.texto)
        elif r.nivel == "alto":
            puntaje -= 25
            razones.append(r.texto)
        mejor: Hueco | None = None
        mejor_p = -1
        for h in huecos:
            local = h.starts_at.astimezone(tz)
            p = 0
            if r.dia is not None and local.weekday() == r.dia:
                p += 10
            if r.franja and _franja(local.hour) == r.franja:
                p += 10
            if r.profesional_id and h.professional_id == r.profesional_id:
                p += 10
            if local.date() == hoy:
                p += 2
            if p > mejor_p:
                mejor, mejor_p = h, p
        if mejor:
            puntaje += mejor_p
        if r.dia is not None or r.franja:
            partes = []
            if r.dia is not None:
                partes.append(f"los {DIAS[r.dia]}")
            if r.franja:
                partes.append(f"por la {r.franja}")
            razones.append("Suele venir " + " ".join(partes))
        if mejor and r.profesional_id == mejor.professional_id:
            razones.append(f"Se atiende con {mejor.professional_name}")
        sugerencias.append(Sugerencia(
            patient_id=pid,
            patient_name=f"{c.paciente.first_name} {c.paciente.last_name}",
            phone=c.paciente.phone,
            whatsapp=c.paciente.whatsapp or c.paciente.phone,
            motivo=c.motivo,
            detalle=c.detalles[0],
            razones=razones,
            riesgo=r.nivel,
            puntaje=puntaje,
            hueco=mejor,
            mensaje=_mensaje(c, clinic.name, mejor, tz, hoy),
        ))
    sugerencias.sort(key=lambda s: (-s.puntaje, s.patient_name))
    return LlamarHoy(huecos=huecos, minutos_libres=sum(h.minutos for h in huecos), sugerencias=sugerencias[:15])


def _mensaje(c: _Candidato, clinica: str, hueco: Hueco | None, tz, hoy: date) -> str:
    que = {
        "ortodoncia": "para su control de ortodoncia",
        "reagendar": "para reagendar su cita",
        "tratamiento": "para continuar con su tratamiento",
        "control": "para su control y limpieza",
    }[c.motivo]
    cuando = f" {_cuando(hueco.starts_at.astimezone(tz), hoy)}" if hueco else " esta semana"
    return (
        f"Hola {c.paciente.first_name}, le saluda {clinica}. Tenemos un espacio disponible{cuando} {que}. "
        "¿Le gustaría que se lo reservemos?"
    )


router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("/call-today", response_model=LlamarHoy)
async def get_llamar_hoy(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return await llamar_hoy(db, current_user)


@router.get("/no-show-risk", response_model=list[RiesgoOut])
async def get_riesgos(
    patient_ids: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    ids = set()
    for x in patient_ids.split(",")[:300]:
        try:
            ids.add(uuid.UUID(x.strip()))
        except ValueError:
            continue
    rs = await riesgos(db, current_user.clinic_id, ids)
    return [RiesgoOut(patient_id=pid, nivel=r.nivel, faltas=r.faltas, total=r.total, texto=r.texto) for pid, r in rs.items()]
