import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DiagnosisCreate(BaseModel):
    fdi_number: str | None = None
    description: str = Field(min_length=1)
    professional_id: uuid.UUID | None = None
    notes: str | None = None


class DiagnosisOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    fdi_number: str | None
    description: str
    notes: str | None
    voided_at: datetime | None = None
    void_reason: str | None = None

    model_config = {"from_attributes": True}
