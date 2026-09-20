import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.core.config import get_settings
from app.modules.ai_assist.models import AiSuggestion
from app.modules.ai_assist.schemas import AiStatus, SuggestionRequest
from app.modules.appointments.models import Appointment
from app.modules.clinical_evolution.models import ClinicalEvolution
from app.modules.diagnoses.models import Diagnosis
from app.modules.medical_history.models import MedicalHistory
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.shared.ai import (
    BASE_SYSTEM_PROMPT,
    AiUnavailable,
    GuardrailViolation,
    check_output,
    get_ai,
)

KIND_INSTRUCTIONS = {
    "resumen_historia": (
        "Resume la historia del paciente para que el profesional la lea en menos de un "
        "minuto antes de la consulta. Ordena por relevancia clínica: alergias y "
        "antecedentes primero. Indica explícitamente qué datos NO constan."
    ),
    "borrador_mensaje": (
        "Redacta un mensaje breve y cordial para enviar al paciente por WhatsApp. "
        "Trátalo de usted. No incluyas datos clínicos sensibles: un mensaje puede "
        "leerlo otra persona en el teléfono."
    ),
    "resumen_visita": (
        "Redacta un resumen de la última visita en lenguaje sencillo para el paciente, "
        "usando solo lo que ya está registrado."
    ),
}


def ai_status() -> AiStatus:
    provider = get_ai()
    settings = get_settings()
    return AiStatus(
        provider=provider.name,
        is_available=provider.is_available,
        model=settings.AI_MODEL if provider.is_available else None,
        message=(
            "El asistente está activo. Todo lo que produce es un borrador que usted revisa."
            if provider.is_available
            else "El asistente no está configurado. Añada ANTHROPIC_API_KEY en el servidor "
            "para activarlo; mientras tanto no se genera ningún texto."
        ),
    )


async def build_context(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> str:
    """Assembles the ONLY facts the assistant is allowed to work from.

    Built server-side from this patient's own rows. Nothing the caller sends
    becomes a fact — a clinician's instruction says what to write, never what
    is true."""
    patient = await get_patient_or_404(db, clinic_id, patient_id)
    lines: list[str] = []

    age = ""
    if patient.birth_date:
        age = f", {(date.today() - patient.birth_date).days // 365} años"
    lines.append(f"PACIENTE: {patient.first_name} {patient.last_name}{age}")

    history = (
        await db.execute(
            select(MedicalHistory)
            .where(MedicalHistory.clinic_id == clinic_id, MedicalHistory.patient_id == patient_id)
            .order_by(MedicalHistory.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if history is None:
        lines.append("ANTECEDENTES: no consta historia clínica registrada.")
    else:
        lines.append("ANTECEDENTES REGISTRADOS:")
        for label, value in [
            ("Alergias", history.allergies),
            ("Medicación habitual", history.medications),
            ("Enfermedades", history.medical_conditions),
            ("Cirugías", history.surgeries),
            ("Hábitos", history.habits),
            ("Motivo de consulta", history.chief_complaint),
        ]:
            lines.append(f"  - {label}: {value if value else 'no consta'}")

    diagnoses = (
        await db.execute(
            select(Diagnosis)
            .where(Diagnosis.clinic_id == clinic_id, Diagnosis.patient_id == patient_id)
            .order_by(Diagnosis.created_at.desc())
            .limit(8)
        )
    ).scalars().all()
    lines.append("DIAGNÓSTICOS YA REGISTRADOS POR UN PROFESIONAL:")
    if not diagnoses:
        lines.append("  - ninguno registrado")
    for d in diagnoses:
        piece = f" (pieza {d.fdi_number})" if d.fdi_number else ""
        lines.append(f"  - {d.created_at.date()}{piece}: {d.description}")

    evolutions = (
        await db.execute(
            select(ClinicalEvolution)
            .where(
                ClinicalEvolution.clinic_id == clinic_id,
                ClinicalEvolution.patient_id == patient_id,
            )
            .order_by(ClinicalEvolution.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    lines.append("ÚLTIMAS EVOLUCIONES:")
    if not evolutions:
        lines.append("  - ninguna registrada")
    for e in evolutions:
        lines.append(f"  - {e.created_at.date()}: {e.procedure}")

    upcoming = (
        await db.execute(
            select(Appointment)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.patient_id == patient_id,
                Appointment.starts_at >= datetime.now(timezone.utc),
                Appointment.status.not_in(("cancelada", "no_asistio")),
            )
            .order_by(Appointment.starts_at)
            .limit(3)
        )
    ).scalars().all()
    lines.append("PRÓXIMAS CITAS:")
    if not upcoming:
        lines.append("  - ninguna agendada")
    for a in upcoming:
        lines.append(f"  - {a.starts_at.strftime('%d/%m/%Y %H:%M')}")

    # Said out loud to the model as well as enforced in code afterwards.
    lines.append(
        "\nNO se te entrega ninguna información económica, y no debes mencionar importes."
    )
    return "\n".join(lines)


async def create_suggestion(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: SuggestionRequest,
) -> AiSuggestion:
    provider = get_ai()
    context = await build_context(db, clinic_id, patient_id)

    user_prompt = (
        f"{KIND_INSTRUCTIONS[payload.kind]}\n\n"
        f"CONTEXTO DEL REGISTRO (única fuente de datos permitida):\n{context}"
    )
    if payload.request:
        user_prompt += (
            f"\n\nINDICACIÓN DEL PROFESIONAL (qué quiere transmitir, no un dato clínico):\n"
            f"{payload.request}"
        )

    try:
        output = await provider.complete(BASE_SYSTEM_PROMPT, user_prompt)
    except AiUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    try:
        check_output(output)
    except GuardrailViolation as exc:
        # The draft is thrown away, not shown with a warning: a violation that
        # still reaches the screen was never really caught.
        await record_audit(
            db, clinic_id=clinic_id, user_id=actor_id, action="blocked", entity_type="ai_suggestion",
            entity_id=str(patient_id), after={"kind": exc.kind, "excerpt": exc.excerpt},
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    settings = get_settings()
    suggestion = AiSuggestion(
        clinic_id=clinic_id,
        patient_id=patient_id,
        kind=payload.kind,
        request=payload.request,
        context_used=context,
        output=output,
        model=settings.AI_MODEL,
        provider=provider.name,
        status="borrador",
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(suggestion)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="ai_suggestion",
        entity_id=str(suggestion.id), after={"kind": payload.kind, "patient_id": str(patient_id)},
    )
    return suggestion


async def get_or_404(db: AsyncSession, clinic_id: uuid.UUID, suggestion_id: uuid.UUID) -> AiSuggestion:
    result = await db.execute(
        select(AiSuggestion).where(
            AiSuggestion.id == suggestion_id, AiSuggestion.clinic_id == clinic_id
        )
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")
    return suggestion


async def decide(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    *,
    accept: bool,
    reason: str | None = None,
) -> AiSuggestion:
    """Records a person's decision about a draft.

    Accepting does NOT write anything into the clinical record. It marks who
    took responsibility for the text; putting it into an evolution or a message
    is a separate, deliberate act by that same person."""
    suggestion = await get_or_404(db, clinic_id, suggestion_id)
    if suggestion.status != "borrador":
        raise HTTPException(status_code=409, detail="La sugerencia ya fue resuelta")

    suggestion.status = "aceptado" if accept else "descartado"
    suggestion.decided_at = datetime.now(timezone.utc)
    suggestion.accepted_by_id = actor_id if accept else None
    suggestion.discard_reason = None if accept else reason
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id,
        action="accept" if accept else "discard",
        entity_type="ai_suggestion", entity_id=str(suggestion_id),
        after={"status": suggestion.status},
    )
    return suggestion


async def list_suggestions(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[AiSuggestion]:
    result = await db.execute(
        select(AiSuggestion)
        .where(AiSuggestion.clinic_id == clinic_id, AiSuggestion.patient_id == patient_id)
        .order_by(AiSuggestion.created_at.desc())
    )
    return list(result.scalars().all())
