import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.messaging.models import MESSAGE_CHANNEL_CODES


class TemplateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    channel: str = "whatsapp"
    body: str = Field(min_length=1)
    is_active: bool = True

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        if value not in MESSAGE_CHANNEL_CODES:
            raise ValueError(f"Canal inválido: {value}")
        return value


class TemplateOut(TemplateIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    patient_id: uuid.UUID
    channel: str = "whatsapp"
    body: str | None = None
    # Either a free body or a template to render with the patient's data.
    template_code: str | None = None
    appointment_id: uuid.UUID | None = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        if value not in MESSAGE_CHANNEL_CODES:
            raise ValueError(f"Canal inválido: {value}")
        return value


class MessageOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID | None
    appointment_id: uuid.UUID | None
    channel: str
    to_address: str
    body: str
    status: str
    provider: str | None
    provider_message_id: str | None
    error: str | None
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class ProviderStatus(BaseModel):
    """What the UI shows before anyone presses send, so the difference between
    a real delivery and a simulation is never a surprise."""

    provider: str
    is_live: bool
    message: str


class DispatchResult(BaseModel):
    due: int
    sent: int
    simulated: int
    failed: int
    skipped: int
