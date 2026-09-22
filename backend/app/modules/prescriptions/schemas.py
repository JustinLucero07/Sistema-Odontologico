import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PrescriptionItemIn(BaseModel):
    medication: str = Field(min_length=1, max_length=200)
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None


class PrescriptionItemOut(PrescriptionItemIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class PrescriptionCreate(BaseModel):
    professional_id: uuid.UUID | None = None
    notes: str | None = None
    items: list[PrescriptionItemIn] = Field(min_length=1)


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    notes: str | None
    items: list[PrescriptionItemOut]
    voided_at: datetime | None = None
    void_reason: str | None = None

    model_config = {"from_attributes": True}
