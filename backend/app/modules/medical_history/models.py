import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class MedicalHistory(UUIDPKMixin, TenantMixin, Base):
    """Append-only: every save inserts a new row, never updates one. The
    current state of a patient's history is simply the latest row by
    created_at — this is the same versioning philosophy as the odontogram,
    so nothing clinically important is ever silently overwritten."""

    __tablename__ = "medical_histories"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Datos médicos
    allergies: Mapped[str | None] = mapped_column(Text)
    medications: Mapped[str | None] = mapped_column(Text)
    medical_conditions: Mapped[str | None] = mapped_column(Text)
    surgeries: Mapped[str | None] = mapped_column(Text)
    habits: Mapped[str | None] = mapped_column(Text)
    is_pregnant: Mapped[bool | None] = mapped_column(Boolean)
    vital_signs: Mapped[str | None] = mapped_column(Text)

    # Datos odontológicos
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    present_illness_history: Mapped[str | None] = mapped_column(Text)
    oral_hygiene: Mapped[str | None] = mapped_column(Text)
    dental_habits: Mapped[str | None] = mapped_column(Text)
    dental_history: Mapped[str | None] = mapped_column(Text)

    # Evaluación
    extraoral_exam: Mapped[str | None] = mapped_column(Text)
    intraoral_exam: Mapped[str | None] = mapped_column(Text)
    soft_tissues: Mapped[str | None] = mapped_column(Text)
    gums: Mapped[str | None] = mapped_column(Text)
    periodontium: Mapped[str | None] = mapped_column(Text)
    tmj: Mapped[str | None] = mapped_column(Text)
    occlusion: Mapped[str | None] = mapped_column(Text)

    observations: Mapped[str | None] = mapped_column(Text)
