import base64
import hashlib
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_settings
from app.modules.clinics.models import Clinic
from app.modules.consents.library import BIBLIOTECA
from app.modules.consents.models import Consent, ConsentTemplate
from app.modules.consents.schemas import (
    ConsentCreate,
    ConsentSign,
    ConsentTemplateCreate,
    ConsentTemplateUpdate,
    PublicSign,
)
from app.modules.patients.models import Patient
from app.modules.patients.service import get_patient_or_404
from app.modules.professionals.models import Professional
from app.shared.voiding import apply_void

# Un enlace de firma a distancia vale 7 días.
DIAS_ENLACE = 7
# Una firma dibujada pesa unas decenas de KB; 400 KB es holgado y evita que
# alguien suba cualquier cosa como «firma».
MAX_FIRMA = 400_000


async def list_templates(
    db: AsyncSession, clinic_id: uuid.UUID, include_inactive: bool = False
) -> list[ConsentTemplate]:
    query = select(ConsentTemplate).where(ConsentTemplate.clinic_id == clinic_id)
    if not include_inactive:
        query = query.where(ConsentTemplate.is_active.is_(True))
    result = await db.execute(query.order_by(ConsentTemplate.name))
    return list(result.scalars().all())


async def update_template(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, template_id: uuid.UUID,
    payload: ConsentTemplateUpdate,
) -> ConsentTemplate:
    """Cambiar una plantilla no toca los consentimientos ya emitidos: cada uno
    guardó su propia copia del texto que el paciente leyó."""
    template = (
        await db.execute(
            select(ConsentTemplate).where(ConsentTemplate.id == template_id, ConsentTemplate.clinic_id == clinic_id)
        )
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
    before = {"name": template.name, "is_active": template.is_active}
    for field, value in payload.model_dump().items():
        setattr(template, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="consent_template",
        entity_id=str(template_id), before=before, after={"name": template.name, "is_active": template.is_active},
    )
    return template


async def create_template(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: ConsentTemplateCreate
) -> ConsentTemplate:
    template = ConsentTemplate(clinic_id=clinic_id, **payload.model_dump())
    db.add(template)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="consent_template",
        entity_id=str(template.id), after={"name": template.name},
    )
    return template


# ---------------------------------------------------------------- Biblioteca


async def library(db: AsyncSession, clinic_id: uuid.UUID) -> list[dict]:
    tiene = {t.name for t in await list_templates(db, clinic_id, include_inactive=True)}
    return [
        {"name": nombre, "procedure_type": tipo, "preview": cuerpo[:240], "added": nombre in tiene}
        for nombre, tipo, cuerpo in BIBLIOTECA
    ]


async def add_from_library(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, nombres: list[str] | None) -> int:
    """Copia a la consulta las plantillas elegidas (o todas) que aún no tenga.
    Quedan como plantillas propias y editables."""
    tiene = {t.name for t in await list_templates(db, clinic_id, include_inactive=True)}
    agregadas = 0
    for nombre, tipo, cuerpo in BIBLIOTECA:
        if nombre in tiene or (nombres is not None and nombre not in nombres):
            continue
        db.add(ConsentTemplate(clinic_id=clinic_id, name=nombre, procedure_type=tipo, body=cuerpo, is_active=True))
        agregadas += 1
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="add_library", entity_type="consent_template",
        entity_id=None, after={"added": agregadas},
    )
    return agregadas


# ---------------------------------------------------------------- Emisión


def _edad(nacimiento: date | None) -> str:
    if nacimiento is None:
        return "edad no registrada"
    hoy = date.today()
    anios = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    return f"{anios} años"


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _rellenar(texto: str, valores: dict[str, str]) -> str:
    for clave, valor in valores.items():
        texto = texto.replace("{" + clave + "}", valor)
    return texto


def huella(titulo: str, cuerpo: str) -> str:
    return hashlib.sha256(f"{titulo}\n\n{cuerpo}".encode("utf-8")).hexdigest()


async def list_consents(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Consent]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Consent)
        .where(Consent.clinic_id == clinic_id, Consent.patient_id == patient_id)
        .order_by(Consent.created_at.desc())
    )
    return list(result.scalars().all())


async def get_consent_or_404(db: AsyncSession, clinic_id: uuid.UUID, consent_id: uuid.UUID) -> Consent:
    consent = (
        await db.execute(select(Consent).where(Consent.id == consent_id, Consent.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if consent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consentimiento no encontrado")
    return consent


async def create_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: ConsentCreate
) -> Consent:
    paciente = await get_patient_or_404(db, clinic_id, patient_id)

    title = payload.title
    body = payload.body
    procedure_type = payload.procedure_type

    if payload.template_id is not None:
        result = await db.execute(
            select(ConsentTemplate).where(
                ConsentTemplate.id == payload.template_id, ConsentTemplate.clinic_id == clinic_id
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
        # Snapshot the wording: the patient consents to this exact text, and a
        # later edit to the template must not change what they agreed to.
        title = title or template.name
        body = body or template.body
        procedure_type = procedure_type or template.procedure_type

    if not title or not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indique una plantilla o escriba el título y el texto del consentimiento",
        )

    profesional = None
    if payload.professional_id is not None:
        profesional = (
            await db.execute(
                select(Professional).where(Professional.id == payload.professional_id, Professional.clinic_id == clinic_id)
            )
        ).scalar_one_or_none()
        if profesional is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesional no encontrado")
    clinica = (await db.execute(select(Clinic).where(Clinic.id == clinic_id))).scalar_one()
    hoy = datetime.now(ZoneInfo(clinica.timezone or "America/Guayaquil")).date()
    # Los datos se escriben en el texto al emitirlo: lo que se firma queda
    # completo y legible por sí mismo, sin depender de la ficha.
    valores = {
        "paciente": f"{paciente.first_name} {paciente.last_name}",
        "cedula": paciente.national_id or "__________",
        "edad": _edad(paciente.birth_date),
        "fecha": _fecha_larga(hoy),
        "ciudad": paciente.city or "Ecuador",
        "clinica": clinica.name,
        "profesional": f"{profesional.first_name} {profesional.last_name}" if profesional else "tratante",
        "registro": (profesional.license_number if profesional and profesional.license_number else "__________"),
        "pieza": (payload.tooth or "").strip() or "indicada por el profesional",
        "procedimiento": title,
    }
    body = _rellenar(body, valores)
    if payload.notes and payload.notes.strip():
        body += f"\n\nObservaciones del profesional: {payload.notes.strip()}"

    consent = Consent(
        clinic_id=clinic_id,
        patient_id=patient_id,
        template_id=payload.template_id,
        professional_id=payload.professional_id,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        title=title,
        procedure_type=procedure_type,
        body=body,
        tooth=(payload.tooth or "").strip() or None,
        status="pendiente",
        content_hash=huella(title, body),
    )
    db.add(consent)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="consent",
        entity_id=str(consent.id), after={"patient_id": str(patient_id), "title": title},
    )
    return consent


# ---------------------------------------------------------------- Firma


def validar_firma(imagen: str | None, obligatoria: bool, quien: str = "la firma") -> str | None:
    """Acepta solo un PNG en data URL de tamaño razonable."""
    if not imagen:
        if obligatoria:
            raise HTTPException(status_code=422, detail=f"Falta {quien}: dibújela en el recuadro.")
        return None
    prefijo = "data:image/png;base64,"
    if not imagen.startswith(prefijo) or len(imagen) > MAX_FIRMA:
        raise HTTPException(status_code=422, detail=f"{quien.capitalize()} no es una imagen válida.")
    try:
        crudo = base64.b64decode(imagen[len(prefijo):], validate=True)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{quien.capitalize()} no es una imagen válida.") from e
    if not crudo.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail=f"{quien.capitalize()} no es una imagen válida.")
    return imagen


def _firmable(consent: Consent) -> None:
    if consent.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este consentimiento está anulado y no se puede firmar")
    if consent.status == "firmado":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este consentimiento ya fue firmado")


async def sign_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, consent_id: uuid.UUID, payload: ConsentSign
) -> Consent:
    consent = await get_consent_or_404(db, clinic_id, consent_id)
    _firmable(consent)

    consent.status = "firmado"
    consent.signed_at = datetime.now(timezone.utc)
    consent.signed_by_name = payload.signed_by_name.strip()
    consent.signature_notes = payload.signature_notes
    consent.signer_id_number = (payload.signer_id_number or "").strip() or None
    consent.signer_relationship = (payload.signer_relationship or "").strip() or None
    consent.signature_image = validar_firma(payload.signature_image, obligatoria=False)
    consent.professional_signature_image = validar_firma(payload.professional_signature_image, obligatoria=False, quien="la firma del profesional")
    consent.witness_name = (payload.witness_name or "").strip() or None
    consent.signed_channel = "presencial"
    consent.sign_token_hash = None

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="sign", entity_type="consent",
        entity_id=str(consent_id),
        after={"signed_by_name": consent.signed_by_name, "drawn": consent.signature_image is not None, "channel": "presencial"},
    )
    return consent


def _huella_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def url_firma(raw: str) -> str:
    return f"{get_settings().PORTAL_BASE_URL.rstrip('/')}/firmar/{raw}"


async def create_sign_link(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, consent_id: uuid.UUID, send_email: bool
) -> dict:
    """Enlace para que el paciente lea y firme desde su teléfono. Se muestra
    una sola vez: solo se guarda su huella. Un enlace nuevo invalida el anterior."""
    consent = await get_consent_or_404(db, clinic_id, consent_id)
    _firmable(consent)
    raw = secrets.token_urlsafe(32)
    consent.sign_token_hash = _huella_token(raw)
    consent.sign_token_expires_at = datetime.now(timezone.utc) + timedelta(days=DIAS_ENLACE)
    url = url_firma(raw)

    enviado = False
    error = None
    if send_email:
        from app.modules.mail import service as correo

        paciente = await get_patient_or_404(db, clinic_id, consent.patient_id)
        clinica = (await db.execute(select(Clinic).where(Clinic.id == clinic_id))).scalar_one()
        if not paciente.email:
            error = "El paciente no tiene correo registrado."
        else:
            try:
                await correo.enviar(
                    db, clinic_id, paciente.email, f"Consentimiento para firmar — {clinica.name}",
                    f"Hola {paciente.first_name}:\n\n{clinica.name} le envía el consentimiento «{consent.title}» "
                    f"para que lo lea y lo firme desde su teléfono:\n\n{url}\n\nEl enlace vence en {DIAS_ENLACE} días.",
                    correo.pagina(clinica, "Consentimiento para firmar", [
                        f"Hola <b>{correo.escapar(paciente.first_name)}</b>:",
                        f"{correo.escapar(clinica.name)} le envía el consentimiento <b>{correo.escapar(consent.title)}</b> "
                        "para que lo lea con calma y lo firme desde su teléfono.",
                        f"El enlace vence en {DIAS_ENLACE} días.",
                    ], ("Leer y firmar", url)),
                )
                enviado = True
                consent.sign_link_sent_at = datetime.now(timezone.utc)
            except (correo.CorreoNoConfigurado, correo.CorreoFallido) as e:
                error = str(e)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="sign_link", entity_type="consent",
        entity_id=str(consent_id), after={"emailed": enviado},
    )
    return {"url": url, "expires_at": consent.sign_token_expires_at, "emailed": enviado, "email_error": error}


async def resolve_public(db: AsyncSession, raw: str) -> tuple[Consent, Patient, Clinic]:
    """Un enlace vencido, usado o inexistente dan la misma respuesta: no se
    revela si existió."""
    consent = (
        await db.execute(select(Consent).where(Consent.sign_token_hash == _huella_token(raw)))
    ).scalar_one_or_none()
    if (
        consent is None
        or consent.voided_at is not None
        or consent.sign_token_expires_at is None
        or consent.sign_token_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=404, detail="Este enlace ya no es válido. Pida uno nuevo a su consulta.")
    paciente = (await db.execute(select(Patient).where(Patient.id == consent.patient_id))).scalar_one()
    clinica = (await db.execute(select(Clinic).where(Clinic.id == consent.clinic_id))).scalar_one()
    return consent, paciente, clinica


async def sign_public(db: AsyncSession, raw: str, payload: PublicSign, ip: str | None, agente: str | None) -> Consent:
    consent, _, _ = await resolve_public(db, raw)
    _firmable(consent)
    if not payload.accept:
        raise HTTPException(status_code=422, detail="Debe confirmar que leyó y acepta el consentimiento.")
    consent.status = "firmado"
    consent.signed_at = datetime.now(timezone.utc)
    consent.signed_by_name = payload.signed_by_name.strip()
    consent.signer_id_number = (payload.signer_id_number or "").strip() or None
    consent.signer_relationship = (payload.signer_relationship or "").strip() or None
    consent.signature_image = validar_firma(payload.signature_image, obligatoria=True)
    consent.signed_channel = "remoto"
    consent.signed_ip = (ip or "")[:64] or None
    consent.signed_user_agent = (agente or "")[:300] or None
    # El enlace se usa una sola vez.
    consent.sign_token_hash = None
    await db.flush()
    await record_audit(
        db, clinic_id=consent.clinic_id, user_id=None, action="sign", entity_type="consent",
        entity_id=str(consent.id), after={"signed_by_name": consent.signed_by_name, "channel": "remoto", "ip": consent.signed_ip},
    )
    return consent


async def void_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, consent_id: uuid.UUID, reason: str
) -> Consent:
    """Un consentimiento no se borra. Si estaba pendiente se anula (emitido por
    error); si estaba firmado, el paciente lo revoca, que es su derecho. En
    ambos casos el texto y la firma originales siguen en la historia."""
    consent = await get_consent_or_404(db, clinic_id, consent_id)
    apply_void(consent, actor_id, reason, "El consentimiento")
    consent.sign_token_hash = None
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id,
        action="revoke" if consent.status == "firmado" else "void", entity_type="consent",
        entity_id=str(consent_id), after={"reason": consent.void_reason},
    )
    return consent
