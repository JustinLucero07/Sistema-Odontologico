import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class ClinicalEvolution(UUIDPKMixin, TenantMixin, Base):
    """What was actually done in a visit.

    Append-only by design: an evolution note is the clinical record of a
    moment, so it is never deleted, and edits leave an audit trail rather than
    quietly replacing what the professional originally wrote."""

    __tablename__ = "clinical_evolutions"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True, index=True
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    procedure: Mapped[str] = mapped_column(Text, nullable=False)
    fdi_numbers: Mapped[str | None] = mapped_column(String(100))
    anesthesia: Mapped[str | None] = mapped_column(String(200))
    materials: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    evolution: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    next_appointment_notes: Mapped[str | None] = mapped_column(Text)
