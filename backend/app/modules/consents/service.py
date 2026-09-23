import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.shared.voiding import apply_void
from app.modules.consents.models import Consent, ConsentTemplate
from app.modules.consents.schemas import ConsentCreate, ConsentSign, ConsentTemplateCreate, ConsentTemplateUpdate
from app.modules.patients.service import get_patient_or_404


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


async def list_consents(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Consent]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Consent)
        .where(Consent.clinic_id == clinic_id, Consent.patient_id == patient_id)
        .order_by(Consent.created_at.desc())
    )
    return list(result.scalars().all())


async def create_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: ConsentCreate
) -> Consent:
    await get_patient_or_404(db, clinic_id, patient_id)

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
        status="pendiente",
    )
    db.add(consent)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="consent",
        entity_id=str(consent.id), after={"patient_id": str(patient_id), "title": title},
    )
    return consent


async def sign_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, consent_id: uuid.UUID, payload: ConsentSign
) -> Consent:
    result = await db.execute(
        select(Consent).where(Consent.id == consent_id, Consent.clinic_id == clinic_id)
    )
    consent = result.scalar_one_or_none()
    if consent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consentimiento no encontrado")
    if consent.status == "firmado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Este consentimiento ya fue firmado"
        )
    if consent.voided_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Este consentimiento está anulado y no se puede firmar"
        )

    consent.status = "firmado"
    consent.signed_at = datetime.now(timezone.utc)
    consent.signed_by_name = payload.signed_by_name
    consent.signature_notes = payload.signature_notes

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="sign", entity_type="consent",
        entity_id=str(consent_id), after={"signed_by_name": payload.signed_by_name},
    )
    return consent


async def void_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, consent_id: uuid.UUID, reason: str
) -> Consent:
    """Un consentimiento no se borra. Si estaba pendiente se anula (emitido por
    error); si estaba firmado, el paciente lo revoca, que es su derecho. En
    ambos casos el texto y la firma originales siguen en la historia."""
    consent = (
        await db.execute(select(Consent).where(Consent.id == consent_id, Consent.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if consent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consentimiento no encontrado")
    apply_void(consent, actor_id, reason, "El consentimiento")
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id,
        action="revoke" if consent.status == "firmado" else "void", entity_type="consent",
        entity_id=str(consent_id), after={"reason": consent.void_reason},
    )
    return consent
