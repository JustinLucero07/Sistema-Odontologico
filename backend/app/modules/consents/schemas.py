import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConsentTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    procedure_type: str | None = None
    body: str = Field(min_length=1)


class ConsentTemplateUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    procedure_type: str | None = None
    body: str = Field(min_length=1)
    is_active: bool = True


class ConsentTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    procedure_type: str | None
    body: str
    is_active: bool

    model_config = {"from_attributes": True}


class ConsentCreate(BaseModel):
    template_id: uuid.UUID | None = None
    professional_id: uuid.UUID | None = None
    title: str | None = None
    procedure_type: str | None = None
    # Left empty when a template is given: the template's wording is copied in.
    body: str | None = None


class ConsentSign(BaseModel):
    signed_by_name: str = Field(min_length=1, max_length=200)
    signature_notes: str | None = None


class ConsentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    template_id: uuid.UUID | None
    professional_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    title: str
    procedure_type: str | None
    body: str
    status: str
    signed_at: datetime | None
    signed_by_name: str | None
    signature_notes: str | None

    model_config = {"from_attributes": True}
