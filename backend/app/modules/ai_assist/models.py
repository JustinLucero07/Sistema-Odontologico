import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin

SUGGESTION_KINDS = [
    ("resumen_historia", "Resumen de la historia clínica"),
    ("borrador_mensaje", "Borrador de mensaje al paciente"),
    ("resumen_visita", "Resumen de la visita para el paciente"),
]
SUGGESTION_KIND_CODES = {code for code, _ in SUGGESTION_KINDS}


class AiSuggestion(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "ai_suggestions"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    # What the clinician asked for, when they asked for something specific.
    request: Mapped[str | None] = mapped_column(Text)
    context_used: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)

    model: Mapped[str | None] = mapped_column(String(80))
    provider: Mapped[str | None] = mapped_column(String(40))

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="borrador")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discard_reason: Mapped[str | None] = mapped_column(Text)
