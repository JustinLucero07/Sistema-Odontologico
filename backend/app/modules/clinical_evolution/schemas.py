import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvolutionCreate(BaseModel):
    appointment_id: uuid.UUID | None = None
    professional_id: uuid.UUID | None = None
    procedure: str = Field(min_length=1)
    fdi_numbers: str | None = None
    anesthesia: str | None = None
    materials: str | None = None
    diagnosis: str | None = None
    evolution: str | None = None
    instructions: str | None = None
    next_appointment_notes: str | None = None


class EvolutionUpdate(BaseModel):
    procedure: str | None = None
    fdi_numbers: str | None = None
    anesthesia: str | None = None
    materials: str | None = None
    diagnosis: str | None = None
    evolution: str | None = None
    instructions: str | None = None
    next_appointment_notes: str | None = None


class EvolutionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None
    professional_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    procedure: str
    fdi_numbers: str | None
    anesthesia: str | None
    materials: str | None
    diagnosis: str | None
    evolution: str | None
    instructions: str | None
    next_appointment_notes: str | None

    model_config = {"from_attributes": True}
