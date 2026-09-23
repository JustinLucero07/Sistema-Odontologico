import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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
    archived_at: datetime | None = None
    archived_reason: str | None = None

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    document_type: str
    description: str | None = None


class DocumentArchiveRequest(BaseModel):
    reason: str = Field(min_length=3)
