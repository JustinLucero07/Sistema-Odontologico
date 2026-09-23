import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.privacy.constants import CONSENT_KINDS, CONSENT_METHODS


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
