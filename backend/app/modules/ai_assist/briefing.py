import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.appointments.models import Appointment
from app.modules.patients.service import get_patient_or_404
from app.shared.ai import AiUnavailable, GuardrailViolation, check_output, get_ai

# Respuestas que en la historia significan «nada que reportar».
_VACIO = {"", "no", "ninguna", "ninguno", "niega", "no refiere", "nada", "n/a", "na", "-", "—", "sin datos"}


class Dato(BaseModel):
    codigo: str
    icono: str
    tono: str  # info | alerta | ok | dinero
    texto: str


class Briefing(BaseModel):
    datos: list[Dato]
    ia_disponible: bool


class BriefingIa(BaseModel):
    texto: str
    modelo: str


def _lleno(v: str | None) -> bool:
    return bool(v) and v.strip().lower().rstrip(".") not in _VACIO


def _hora(dt: datetime) -> str:
    return dt.strftime("%H:%M")


_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _fecha(d: date) -> str:
    return f"{d.day} {_MESES[d.month - 1]} {d.year}"


async def armar(db: AsyncSession, user: CurrentUser, patient_id: uuid.UUID) -> list[Dato]:
    from zoneinfo import ZoneInfo

    from app.modules.clinics.models import Clinic

    clinic_id = user.clinic_id
    p = await get_patient_or_404(db, clinic_id, patient_id)
    puede = user.has_permission
    clinic = await db.get(Clinic, clinic_id)
    try:
        tz = ZoneInfo(clinic.timezone or "America/Guayaquil")
    except Exception:  # noqa: BLE001
        tz = ZoneInfo("UTC")
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(tz).date()
    datos: list[Dato] = []

    if puede("appointments:read"):
        from app.modules.professionals.models import Professional
        from app.modules.treatments.models import Treatment

        proxima = (
            await db.execute(
                select(Appointment, Professional, Treatment)
                .join(Professional, Professional.id == Appointment.professional_id)
                .outerjoin(Treatment, Treatment.id == Appointment.treatment_id)
                .where(
                    Appointment.clinic_id == clinic_id,
                    Appointment.patient_id == patient_id,
                    Appointment.ends_at >= ahora,
                    Appointment.status.notin_(["cancelada", "no_asistio", "atendida"]),
                )
                .order_by(Appointment.starts_at)
                .limit(1)
            )
        ).first()
        if proxima:
            a, prof, trat = proxima
            local = a.starts_at.astimezone(tz)
            cuando = f"Hoy a las {_hora(local)}" if local.date() == hoy else f"Próxima cita: {_fecha(local.date())}, {_hora(local)}"
            que = trat.name if trat else (a.notes or "consulta")
            datos.append(Dato(
                codigo="cita", icono="event", tono="info",
                texto=f"{cuando} con {prof.first_name} {prof.last_name} · {que}"
                + (" (por confirmar)" if a.status == "programada" else ""),
            ))
        else:
            datos.append(Dato(codigo="cita", icono="event_busy", tono="alerta", texto="Sin próxima cita agendada"))

        pasadas = (
            await db.execute(
                select(Appointment.starts_at)
                .where(Appointment.clinic_id == clinic_id, Appointment.patient_id == patient_id, Appointment.status == "atendida")
                .order_by(Appointment.starts_at.desc())
                .limit(1)
            )
        ).scalar()
        faltas = await db.scalar(
            select(func.count()).select_from(Appointment).where(
                Appointment.clinic_id == clinic_id, Appointment.patient_id == patient_id,
                Appointment.status == "no_asistio", Appointment.starts_at >= ahora - timedelta(days=365),
            )
        )
        if not pasadas:
            datos.append(Dato(codigo="nuevo", icono="waving_hand", tono="info", texto="Paciente nuevo: aún no tiene citas atendidas"))
        if faltas:
            datos.append(Dato(
                codigo="faltas", icono="event_busy", tono="alerta",
                texto=f"Faltó a {faltas} {'cita' if faltas == 1 else 'citas'} en el último año",
            ))

    if puede("medical_history:read"):
        from app.modules.medical_history.models import MedicalHistory

        h = (
            await db.execute(
                select(MedicalHistory)
                .where(MedicalHistory.clinic_id == clinic_id, MedicalHistory.patient_id == patient_id)
                .order_by(MedicalHistory.created_at.desc())
                .limit(1)
            )
        ).scalar()
        if h is None:
            datos.append(Dato(codigo="historia", icono="assignment_late", tono="alerta", texto="Sin historia clínica registrada"))
        else:
            if _lleno(h.allergies):
                datos.append(Dato(codigo="alergias", icono="warning", tono="alerta", texto=f"Alergias: {h.allergies.strip()}"))
            if _lleno(h.medical_conditions):
                datos.append(Dato(codigo="condiciones", icono="favorite", tono="alerta", texto=f"Condiciones médicas: {h.medical_conditions.strip()}"))
            if _lleno(h.medications):
                datos.append(Dato(codigo="medicacion", icono="medication", tono="info", texto=f"Medicación: {h.medications.strip()}"))
            if h.is_pregnant:
                datos.append(Dato(codigo="embarazo", icono="pregnant_woman", tono="alerta", texto="Embarazada (según la historia)"))

    if clinic.orthodontics_enabled and puede("orthodontics:read"):
        from app.modules.orthodontics.models import OrthoCase, OrthoControl

        caso = (
            await db.execute(
                select(OrthoCase)
                .where(OrthoCase.clinic_id == clinic_id, OrthoCase.patient_id == patient_id,
                       OrthoCase.status.in_(["activo", "retencion", "pausa"]))
                .limit(1)
            )
        ).scalar()
        if caso:
            controles = (
                await db.execute(select(OrthoControl).where(OrthoControl.case_id == caso.id).order_by(OrthoControl.number))
            ).scalars().all()
            siguiente = next((c for c in controles if c.attended_on is None), None)
            atrasados = sum(1 for c in controles if c.attended_on is None and c.planned_on and c.planned_on < hoy)
            texto = f"Ortodoncia ORT-{caso.number:04d}"
            if siguiente:
                texto += f" · toca el control {siguiente.number:02d} de {len(controles)}"
            if caso.stage:
                texto += f" ({caso.stage})"
            datos.append(Dato(codigo="ortodoncia", icono="sentiment_very_satisfied", tono="info", texto=texto))
            if atrasados:
                datos.append(Dato(
                    codigo="orto_atrasos", icono="schedule", tono="alerta",
                    texto=f"Lleva {atrasados} {'control atrasado' if atrasados == 1 else 'controles atrasados'}",
                ))
            if caso.has_tad == "si":
                datos.append(Dato(codigo="tad", icono="push_pin", tono="info", texto="Tiene TAD (microtornillos) colocados"))
            if caso.special_attention:
                datos.append(Dato(
                    codigo="atencion", icono="priority_high", tono="alerta",
                    texto="Atención especial" + (f": {caso.special_attention_note}" if caso.special_attention_note else ""),
                ))

    if puede("treatments:read"):
        from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
        from app.modules.treatments.models import Treatment

        pendientes = (
            await db.execute(
                select(Treatment.name, TreatmentPlanItem.fdi_number)
                .join(TreatmentPlan, TreatmentPlan.id == TreatmentPlanItem.plan_id)
                .join(Treatment, Treatment.id == TreatmentPlanItem.treatment_id)
                .where(TreatmentPlan.clinic_id == clinic_id, TreatmentPlan.patient_id == patient_id,
                       TreatmentPlanItem.status.in_(["aprobado", "en_progreso"]))
            )
        ).all()
        if pendientes:
            nombres = [f"{n}{' ' + f if f else ''}" for n, f in pendientes[:3]]
            extra = f" y {len(pendientes) - 3} más" if len(pendientes) > 3 else ""
            datos.append(Dato(
                codigo="pendientes", icono="assignment", tono="info",
                texto=f"{len(pendientes)} {'tratamiento aprobado pendiente' if len(pendientes) == 1 else 'tratamientos aprobados pendientes'}: {', '.join(nombres)}{extra}",
            ))
    if puede("budgets:read"):
        from app.modules.budgets.models import Budget

        por_responder = await db.scalar(
            select(func.count()).select_from(Budget).where(
                Budget.clinic_id == clinic_id, Budget.patient_id == patient_id, Budget.status.in_(["enviado", "visto"])
            )
        )
        if por_responder:
            datos.append(Dato(
                codigo="presupuesto", icono="request_quote", tono="info",
                texto=f"{por_responder} {'presupuesto espera' if por_responder == 1 else 'presupuestos esperan'} su respuesta",
            ))
    if puede("consents:read"):
        from app.modules.consents.models import Consent

        sin_firma = await db.scalar(
            select(func.count()).select_from(Consent).where(
                Consent.clinic_id == clinic_id, Consent.patient_id == patient_id,
                Consent.status == "pendiente", Consent.voided_at.is_(None),
            )
        )
        if sin_firma:
            datos.append(Dato(
                codigo="consentimiento", icono="draw", tono="alerta",
                texto=f"{sin_firma} {'consentimiento pendiente' if sin_firma == 1 else 'consentimientos pendientes'} de firma",
            ))

    if puede("evolutions:read"):
        from app.modules.clinical_evolution.models import ClinicalEvolution

        ev = (
            await db.execute(
                select(ClinicalEvolution)
                .where(ClinicalEvolution.clinic_id == clinic_id, ClinicalEvolution.patient_id == patient_id)
                .order_by(ClinicalEvolution.created_at.desc())
                .limit(1)
            )
        ).scalar()
        if ev:
            proc = ev.procedure.strip().split("\n")[0][:120]
            datos.append(Dato(
                codigo="ultima", icono="history", tono="info",
                texto=f"Última atención: {_fecha(ev.created_at.astimezone(tz).date())} · {proc}"
                + (f" (piezas {ev.fdi_numbers})" if ev.fdi_numbers else ""),
            ))

    if puede("payments:read"):
        from app.modules.payments.service import get_statement

        cuenta = await get_statement(db, clinic_id, patient_id)
        if cuenta.balance > 0:
            texto = f"Debe ${cuenta.balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if cuenta.overdue_amount and cuenta.overdue_amount > 0:
                texto += f" (vencido ${cuenta.overdue_amount:,.2f})".replace(",", "X").replace(".", ",").replace("X", ".")
            datos.append(Dato(codigo="saldo", icono="account_balance_wallet", tono="dinero", texto=texto))
        elif cuenta.balance < 0:
            datos.append(Dato(codigo="saldo", icono="savings", tono="ok", texto="Tiene saldo a favor"))
        else:
            datos.append(Dato(codigo="saldo", icono="check_circle", tono="ok", texto="Al día con sus pagos"))

    if p.birth_date:
        try:
            este = p.birth_date.replace(year=hoy.year)
        except ValueError:  # 29 de febrero
            este = date(hoy.year, 3, 1)
        dias = (este - hoy).days
        if 0 <= dias <= 7:
            edad = hoy.year - p.birth_date.year
            datos.append(Dato(
                codigo="cumple", icono="cake", tono="ok",
                texto=f"{'Hoy cumple' if dias == 0 else f'Cumple en {dias} días'} {edad} años",
            ))
    return datos


SISTEMA_RESUMEN = (
    "Redactas el resumen previo a la atención de un paciente para el odontólogo o la recepción. "
    "Usa SOLO los datos de la lista; si algo no está en la lista, no lo menciones. "
    "Escribe 2 a 4 oraciones en español neutro, en tono profesional y directo, empezando por lo "
    "más importante para atenderlo hoy (alertas médicas primero). No uses viñetas ni títulos. "
    "No diagnostiques, no recomiendes tratamientos y no menciones dinero ni pagos."
)


async def narrar(db: AsyncSession, user: CurrentUser, patient_id: uuid.UUID) -> BriefingIa:
    from app.core.config import get_settings
    from app.shared.ai import BASE_SYSTEM_PROMPT

    proveedor = get_ai()
    if not proveedor.is_available:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="El asistente de IA no está configurado.")
    datos = [d for d in await armar(db, user, patient_id) if d.tono != "dinero" and d.codigo != "saldo"]
    if not datos:
        raise HTTPException(status_code=422, detail="No hay datos suficientes para resumir.")
    lista = "\n".join(f"- {d.texto}" for d in datos)
    try:
        texto = await proveedor.complete(
            f"{BASE_SYSTEM_PROMPT}\n\n{SISTEMA_RESUMEN}",
            f"DATOS DEL PACIENTE (única fuente permitida):\n{lista}\n\nRedacta el resumen.",
        )
    except AiUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    try:
        check_output(texto)
    except GuardrailViolation as exc:
        await record_audit(
            db, clinic_id=user.clinic_id, user_id=user.id, action="blocked", entity_type="ai_briefing",
            entity_id=str(patient_id), after={"kind": exc.kind, "excerpt": exc.excerpt},
        )
        await db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await record_audit(
        db, clinic_id=user.clinic_id, user_id=user.id, action="create", entity_type="ai_briefing",
        entity_id=str(patient_id), after={"datos": len(datos)},
    )
    await db.commit()
    return BriefingIa(texto=texto, modelo=get_settings().AI_MODEL)


router = APIRouter(prefix="/api/v1/patients/{patient_id}/briefing", tags=["ai"])


@router.get("", response_model=Briefing)
async def get_briefing(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    return Briefing(datos=await armar(db, current_user, patient_id), ia_disponible=get_ai().is_available)


@router.post("/ai", response_model=BriefingIa)
async def post_briefing_ai(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    return await narrar(db, current_user, patient_id)

