import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.laboratory.constants import LAB_ORDER_STATUS_CODES, LAB_WORK_TYPE_CODES
from app.modules.odontogram.constants import VALID_FDI_NUMBERS


class LaboratoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    default_turnaround_days: int | None = Field(default=None, ge=1, le=365)
    notes: str | None = None
    is_active: bool = True


class LaboratoryOut(LaboratoryIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class LabOrderCreate(BaseModel):
    patient_id: uuid.UUID
    laboratory_id: uuid.UUID
    work_type: str
    description: str = Field(min_length=1, max_length=400)
    professional_id: uuid.UUID | None = None
    treatment_plan_item_id: uuid.UUID | None = None
    fdi_numbers: list[str] = Field(default_factory=list)
    shade: str | None = Field(default=None, max_length=40)
    material: str | None = Field(default=None, max_length=120)
    due_on: date | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None

    @field_validator("work_type")
    @classmethod
    def validate_work_type(cls, value: str) -> str:
        if value not in LAB_WORK_TYPE_CODES:
            raise ValueError(f"Tipo de trabajo inválido: {value}")
        return value

    @field_validator("fdi_numbers")
    @classmethod
    def validate_fdi(cls, value: list[str]) -> list[str]:
        invalid = [n for n in value if n not in VALID_FDI_NUMBERS]
        if invalid:
            raise ValueError(f"Números FDI inválidos: {', '.join(invalid)}")
        return value


class LabOrderStatusUpdate(BaseModel):
    status: str
    note: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in LAB_ORDER_STATUS_CODES:
            raise ValueError(f"Estado inválido: {value}")
        return value


class LabOrderEventOut(BaseModel):
    id: uuid.UUID
    status: str
    note: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LabOrderOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str | None
    laboratory_id: uuid.UUID
    laboratory_name: str | None
    professional_id: uuid.UUID | None
    treatment_plan_item_id: uuid.UUID | None
    work_type: str
    description: str
    fdi_numbers: list[str] | None
    shade: str | None
    material: str | None
    status: str
    sent_on: date | None
    due_on: date | None
    received_on: date | None
    cost: Decimal | None
    notes: str | None
    created_at: datetime
    events: list[LabOrderEventOut]
    # Derived: how late the case is against its due date, if it has one.
    days_overdue: int | None
