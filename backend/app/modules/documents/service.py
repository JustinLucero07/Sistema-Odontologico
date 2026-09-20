import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.documents.models import DOCUMENT_TYPE_CODES, Document
from app.modules.patients.service import get_patient_or_404
from app.shared.storage import get_storage

# Generous enough for a scanned consent or a panoramic, small enough that a
# mistaken upload can't fill the disk.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


async def list_documents(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Document]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        select(Document)
        .where(Document.clinic_id == clinic_id, Document.patient_id == patient_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_or_404(db: AsyncSession, clinic_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.clinic_id == clinic_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    return document


async def upload_document(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    title: str,
    document_type: str,
    description: str | None,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> Document:
    await get_patient_or_404(db, clinic_id, patient_id)

    if document_type not in DOCUMENT_TYPE_CODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de documento inválido")
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el máximo de 25 MB",
        )

    storage_key = await get_storage().save(clinic_id, filename, content)

    document = Document(
        clinic_id=clinic_id,
        patient_id=patient_id,
        uploaded_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        document_type=document_type,
        title=title,
        description=description,
        storage_key=storage_key,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
    )
    db.add(document)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="document",
        entity_id=str(document.id), after={"title": title, "type": document_type},
    )
    return document


async def read_document(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, document_id: uuid.UUID):
    document = await get_or_404(db, clinic_id, document_id)
    content = await get_storage().read(document.storage_key)
    # Who downloaded which clinical file is itself worth recording.
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="download", entity_type="document",
        entity_id=str(document_id), after={"title": document.title},
    )
    return document, content
