import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    uploaded_by_id: uuid.UUID | None
    created_at: datetime
    document_type: str
    title: str
    description: str | None
    original_filename: str
    mime_type: str | None
    size_bytes: int | None

    model_config = {"from_attributes": True}
