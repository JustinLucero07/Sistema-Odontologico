import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.odontogram.constants import (
    TOOTH_CONDITION_CODES,
    TOOTH_SURFACE_CODES,
    VALID_FDI_NUMBERS,
)


class ToothConditionIn(BaseModel):
    fdi_number: str
    surface: str
    condition: str
    notes: str | None = None

    @field_validator("fdi_number")
    @classmethod
    def validate_fdi(cls, value: str) -> str:
        if value not in VALID_FDI_NUMBERS:
            raise ValueError(f"Número FDI inválido: {value}")
        return value

    @field_validator("surface")
    @classmethod
    def validate_surface(cls, value: str) -> str:
        if value not in TOOTH_SURFACE_CODES:
            raise ValueError(f"Superficie inválida: {value}")
        return value

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str) -> str:
        if value not in TOOTH_CONDITION_CODES:
            raise ValueError(f"Condición inválida: {value}")
        return value


class ToothConditionOut(ToothConditionIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class OdontogramCreate(BaseModel):
    professional_id: uuid.UUID | None = None
    notes: str | None = None
    conditions: list[ToothConditionIn] = Field(default_factory=list)


class OdontogramOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    previous_odontogram_id: uuid.UUID | None
    notes: str | None
    type: str
    conditions: list[ToothConditionOut]

    model_config = {"from_attributes": True}


class OdontogramSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    type: str

    model_config = {"from_attributes": True}
