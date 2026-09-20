import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.ai_assist.models import SUGGESTION_KIND_CODES


class SuggestionRequest(BaseModel):
    kind: str
    # Free-form instruction from the clinician, e.g. "avísale que debe traer la
    # férula". Never a source of clinical facts — only of intent.
    request: str | None = Field(default=None, max_length=600)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        if value not in SUGGESTION_KIND_CODES:
            raise ValueError(f"Tipo de sugerencia inválido: {value}")
        return value


class SuggestionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    kind: str
    request: str | None
    context_used: str
    output: str
    model: str | None
    provider: str | None
    status: str
    created_by_id: uuid.UUID | None
    created_at: datetime
    accepted_by_id: uuid.UUID | None
    decided_at: datetime | None
    discard_reason: str | None

    model_config = {"from_attributes": True}


class DiscardRequest(BaseModel):
    reason: str | None = None


class AiStatus(BaseModel):
    """Shown before anyone asks for a draft, so an unconfigured assistant is
    never mistaken for one that had nothing to say."""

    provider: str
    is_available: bool
    model: str | None
    message: str
