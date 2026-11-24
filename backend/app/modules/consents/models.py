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
    signed_by_name: Mapped[str | None] = mapped_column(String(200))
    signature_notes: Mapped[str | None] = mapped_column(Text)

    tooth: Mapped[str | None] = mapped_column(String(60))
    signer_id_number: Mapped[str | None] = mapped_column(String(20))
    signer_relationship: Mapped[str | None] = mapped_column(String(60))
    signature_image: Mapped[str | None] = mapped_column(Text)
    professional_signature_image: Mapped[str | None] = mapped_column(Text)
    witness_name: Mapped[str | None] = mapped_column(String(200))
    signed_channel: Mapped[str | None] = mapped_column(String(12))
    signed_ip: Mapped[str | None] = mapped_column(String(64))
    signed_user_agent: Mapped[str | None] = mapped_column(String(300))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    # Enlace de firma a distancia: solo se guarda su huella.
    sign_token_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    sign_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sign_link_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
