import struct
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.imaging.models import IMAGE_TYPE_CODES, ClinicalImage
from app.modules.odontogram.constants import VALID_FDI_NUMBERS
from app.modules.patients.service import get_patient_or_404
from app.shared.storage import get_storage

# A panoramic from a modern sensor runs 5–15 MB; CBCT exports and 24-megapixel
# intraoral photos go further, so this ceiling is higher than for documents.
MAX_IMAGE_BYTES = 60 * 1024 * 1024

# Only formats a browser can actually display. A DICOM file would upload
# happily and then show the viewer a blank frame, so it is refused here rather
# than discovered by the dentist at the chair.
ALLOWED_MIME_PREFIXES = ("image/",)
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp", "image/tiff"}


def _read_dimensions(content: bytes) -> tuple[int | None, int | None]:
    """Pixel size straight from the file header — PNG and JPEG only.

    Knowing the dimensions lets the viewer reserve the right space before the
    bytes arrive, so the page does not jump. It is a nicety, not a
    requirement: anything unrecognised simply returns no size."""
    try:
        if content[:8] == b"\x89PNG\r\n\x1a\n" and content[12:16] == b"IHDR":
            width, height = struct.unpack(">II", content[16:24])
            return int(width), int(height)

        if content[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(content):
                if content[i] != 0xFF:
                    i += 1
                    continue
                marker = content[i + 1]
                # SOF0–SOF15, excluding the non-frame markers in that range.
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    height, width = struct.unpack(">HH", content[i + 5 : i + 9])
                    return int(width), int(height)
                i += 2 + struct.unpack(">H", content[i + 2 : i + 4])[0]
    except (struct.error, IndexError):
        return None, None
    return None, None


async def list_images(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    include_archived: bool = False,
) -> list[ClinicalImage]:
    await get_patient_or_404(db, clinic_id, patient_id)
    query = select(ClinicalImage).where(
        ClinicalImage.clinic_id == clinic_id, ClinicalImage.patient_id == patient_id
    )
    if not include_archived:
        query = query.where(ClinicalImage.archived_at.is_(None))
    # Sorted by when the study was taken, falling back to upload time for the
    # ones whose date nobody entered.
    result = await db.execute(
        query.order_by(ClinicalImage.taken_on.desc().nullslast(), ClinicalImage.created_at.desc())
    )
    return list(result.scalars().all())


async def get_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, image_id: uuid.UUID
) -> ClinicalImage:
    result = await db.execute(
        select(ClinicalImage).where(
            ClinicalImage.id == image_id, ClinicalImage.clinic_id == clinic_id
        )
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagen no encontrada")
    return image


def _parse_fdi_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    numbers = [n.strip() for n in raw.split(",") if n.strip()]
    invalid = [n for n in numbers if n not in VALID_FDI_NUMBERS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Números FDI inválidos: {', '.join(invalid)}",
        )
    return numbers or None


async def upload_image(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    title: str,
    image_type: str,
    description: str | None,
    taken_on: date | None,
    fdi_numbers: str | None,
    professional_id: uuid.UUID | None,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> ClinicalImage:
    await get_patient_or_404(db, clinic_id, patient_id)

    if image_type not in IMAGE_TYPE_CODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de imagen inválido")
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen supera el máximo de 60 MB",
        )
    if mime_type and not (
        mime_type in ALLOWED_MIME_TYPES or mime_type.startswith(ALLOWED_MIME_PREFIXES)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen que el visor pueda mostrar",
        )
    if taken_on and taken_on > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha del estudio no puede ser futura",
        )

    parsed_fdi = _parse_fdi_list(fdi_numbers)
    width, height = _read_dimensions(content)
    storage_key = await get_storage().save(clinic_id, filename, content)

    image = ClinicalImage(
        clinic_id=clinic_id,
        patient_id=patient_id,
        professional_id=professional_id,
        uploaded_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
        image_type=image_type,
        title=title,
        description=description,
        taken_on=taken_on,
        fdi_numbers=parsed_fdi,
        storage_key=storage_key,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
        width=width,
        height=height,
    )
    db.add(image)
    await db.flush()
    await record_audit(
        db,
        clinic_id=clinic_id,
        user_id=actor_id,
        action="create",
        entity_type="clinical_image",
        entity_id=str(image.id),
        after={"title": title, "type": image_type, "teeth": parsed_fdi},
    )
    return image


async def read_image(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, image_id: uuid.UUID
):
    image = await get_or_404(db, clinic_id, image_id)
    content = await get_storage().read(image.storage_key)
    # Who opened which radiograph is itself worth recording.
    await record_audit(
        db,
        clinic_id=clinic_id,
        user_id=actor_id,
        action="download",
        entity_type="clinical_image",
        entity_id=str(image_id),
        after={"title": image.title},
    )
    return image, content


async def archive_image(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    image_id: uuid.UUID,
    reason: str,
) -> ClinicalImage:
    """Withdraws an image from the active study list without destroying it.

    The bytes stay in storage: a radiograph that was acted on clinically is
    part of the record even once it turns out to be the wrong patient's, and
    proving which image was seen at the time is exactly what an archive is
    for."""
    image = await get_or_404(db, clinic_id, image_id)
    if image.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La imagen ya está archivada"
        )
    if not reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Indique el motivo del archivado"
        )

    image.archived_at = datetime.now(timezone.utc)
    image.archived_by_id = actor_id
    image.archived_reason = reason.strip()
    await db.flush()
    await record_audit(
        db,
        clinic_id=clinic_id,
        user_id=actor_id,
        action="archive",
        entity_type="clinical_image",
        entity_id=str(image_id),
        after={"reason": image.archived_reason},
    )
    return image
