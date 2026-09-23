import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin
from app.shared.voiding import VoidableMixin


class ConsentTemplate(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    """Reusable wording per procedure (extracción, endodoncia, implante…)."""

    __tablename__ = "consent_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    procedure_type: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Consent(UUIDPKMixin, TenantMixin, VoidableMixin, Base):
    """A consent given by a specific patient for a specific procedure.

    The wording is copied into `body` when the consent is created rather than
    referenced from the template: what the patient agreed to must stay exactly
    as it was on that day, even if the clinic later edits the template."""

    __tablename__ = "consents"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consent_templates.id"), nullable=True
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    procedure_type: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Who physically signed — the patient or a guardian. A cryptographic
    # signature belongs to the digital-signature phase; this records the
    # in-person signing that happens today.
    signed_by_name: Mapped[str | None] = mapped_column(String(200))
    signature_notes: Mapped[str | None] = mapped_column(Text)
