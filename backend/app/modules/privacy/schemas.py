import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.privacy.constants import CONSENT_KINDS, CONSENT_METHODS, RIGHTS_KINDS, RIGHTS_STATUSES


class ConsentCreate(BaseModel):
    kind: str
    granted: bool = True
    method: str = "firma_presencial"
    signed_by_name: str | None = Field(default=None, max_length=200)
    notes: str | None = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        if value not in CONSENT_KINDS:
            raise ValueError(f"Tipo de registro desconocido: {value}")
        return value

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        if value not in CONSENT_METHODS:
            raise ValueError(f"Método desconocido: {value}")
        return value


class ConsentOut(BaseModel):
    id: uuid.UUID
    kind: str
    granted: bool
    policy_version: str
    method: str
    signed_by_name: str | None
    notes: str | None
    recorded_by_id: uuid.UUID | None
    recorded_by_name: str | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class PrivacyStatus(BaseModel):
    """Estado actual (el último registro de cada tipo) y la historia completa."""

    current_policy_version: str
    privacy_notice: ConsentOut | None
    communications: ConsentOut | None
    notice_outdated: bool
    history: list[ConsentOut]


class AccessEntry(BaseModel):
    at: datetime
    action: str
    user_name: str | None


class LegalController(BaseModel):
    """Identidad del responsable del tratamiento: la clínica. Es lo que el
    aviso de privacidad tiene que decirle al paciente."""

    name: str
    legal_name: str | None
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    privacy_policy_version: str
    confidentiality_version: str
    # Identidad visual para los documentos impresos.
    legal_rep_name: str | None = None
    dpo_name: str | None = None
    dpo_email: str | None = None
    health_permit_number: str | None = None
    record_retention_years: int = 15
    privacy_extra: str | None = None
    terms_version: str = ""
    logo_data: str | None = None
    primary_color: str | None = None
    slogan: str | None = None
    document_footer: str | None = None


class LegalSection(BaseModel):
    title: str
    paragraphs: list[str]


class LegalDocument(BaseModel):
    code: str
    title: str
    version: str
    sections: list[LegalSection]


class RightsRequestIn(BaseModel):
    patient_id: uuid.UUID | None = None
    requester_name: str = Field(min_length=2, max_length=200)
    requester_id_number: str | None = Field(default=None, max_length=20)
    contact: str | None = Field(default=None, max_length=200)
    kind: str
    details: str | None = Field(default=None, max_length=4000)
    received_on: date | None = None
    status: str = "pendiente"
    response: str | None = Field(default=None, max_length=4000)

    @field_validator("kind")
    @classmethod
    def _kind(cls, v):
        if v not in RIGHTS_KINDS:
            raise ValueError("Tipo de solicitud no válido")
        return v

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v not in RIGHTS_STATUSES:
            raise ValueError("Estado no válido")
        return v


class RightsRequestOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID | None
    patient_name: str | None = None
    requester_name: str
    requester_id_number: str | None
    contact: str | None
    kind: str
    kind_label: str = ""
    details: str | None
    received_on: date
    due_on: date
    status: str
    status_label: str = ""
    response: str | None
    resolved_on: date | None
    overdue: bool = False
    days_left: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
