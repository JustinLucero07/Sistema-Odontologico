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
    tooth: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=1000)


class ConsentSign(BaseModel):
    signed_by_name: str = Field(min_length=1, max_length=200)
    signature_notes: str | None = None
    signer_id_number: str | None = Field(default=None, max_length=20)
    # «paciente», o el parentesco del representante legal (madre, padre, tutor…)
    signer_relationship: str | None = Field(default=None, max_length=60)
    signature_image: str | None = None
    professional_signature_image: str | None = None
    witness_name: str | None = Field(default=None, max_length=200)


class PublicSign(BaseModel):
    signed_by_name: str = Field(min_length=3, max_length=200)
    signer_id_number: str | None = Field(default=None, max_length=20)
    signer_relationship: str | None = Field(default=None, max_length=60)
    signature_image: str
    accept: bool


class SignLinkRequest(BaseModel):
    send_email: bool = False


class SignLinkOut(BaseModel):
    url: str
    expires_at: datetime
    emailed: bool
    email_error: str | None


class LibraryAdd(BaseModel):
    # Sin nombres: agrega todas las que falten.
    names: list[str] | None = None


class PublicConsentView(BaseModel):
    clinic_name: str
    clinic_logo: str | None
    clinic_color: str | None
    patient_name: str
    title: str
    body: str
    expires_at: datetime


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
    tooth: str | None = None
    signer_id_number: str | None = None
    signer_relationship: str | None = None
    signature_image: str | None = None
    professional_signature_image: str | None = None
    witness_name: str | None = None
    signed_channel: str | None = None
    signed_ip: str | None = None
    content_hash: str | None = None
    sign_token_expires_at: datetime | None = None
    sign_link_sent_at: datetime | None = None

    voided_at: datetime | None = None
    void_reason: str | None = None

    model_config = {"from_attributes": True}
