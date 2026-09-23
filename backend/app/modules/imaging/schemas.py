import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ClinicalImageOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None
    uploaded_by_id: uuid.UUID | None
    created_at: datetime
    image_type: str
    title: str
    description: str | None
    taken_on: date | None
    fdi_numbers: list[str] | None
    original_filename: str
    mime_type: str | None
    size_bytes: int | None
    width: int | None
    height: int | None
    archived_at: datetime | None
    archived_reason: str | None

    model_config = {"from_attributes": True}


class ImageArchiveRequest(BaseModel):
    """Archiving demands a reason. Without one the record says an image was
    withdrawn but not why, which is exactly the question asked later."""

    reason: str


class ImageUpdate(BaseModel):
    """Datos descriptivos de la imagen. El archivo en sí no se cambia: si la
    imagen está mal, se archiva y se sube la correcta."""

    title: str = Field(min_length=1, max_length=200)
    image_type: str
    description: str | None = None
    taken_on: date | None = None
    fdi_numbers: list[str] = Field(default_factory=list)
