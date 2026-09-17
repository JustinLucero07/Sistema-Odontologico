import uuid
from datetime import datetime

from pydantic import BaseModel


class MedicalHistoryCreate(BaseModel):
    allergies: str | None = None
    medications: str | None = None
    medical_conditions: str | None = None
    surgeries: str | None = None
    habits: str | None = None
    is_pregnant: bool | None = None
    vital_signs: str | None = None

    chief_complaint: str | None = None
    present_illness_history: str | None = None
    oral_hygiene: str | None = None
    dental_habits: str | None = None
    dental_history: str | None = None

    extraoral_exam: str | None = None
    intraoral_exam: str | None = None
    soft_tissues: str | None = None
    gums: str | None = None
    periodontium: str | None = None
    tmj: str | None = None
    occlusion: str | None = None

    observations: str | None = None


class MedicalHistoryOut(MedicalHistoryCreate):
    id: uuid.UUID
    patient_id: uuid.UUID
    created_by_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
