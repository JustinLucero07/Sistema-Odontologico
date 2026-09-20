import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin

MESSAGE_CHANNELS = [
    ("whatsapp", "WhatsApp"),
    ("sms", "SMS"),
    ("email", "Correo electrónico"),
]
MESSAGE_CHANNEL_CODES = {code for code, _ in MESSAGE_CHANNELS}


class MessageTemplate(UUIDPKMixin, TenantMixin, Base):
    """A reusable body with {placeholders} the clinic can edit.

    Templates are per clinic because the tone of a reminder is part of how a
    practice presents itself, and a shared default would be wrong for most."""

    __tablename__ = "message_templates"
    __table_args__ = (UniqueConstraint("clinic_id", "code", name="uq_template_code"),)

    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="whatsapp")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OutboundMessage(UUIDPKMixin, TenantMixin, Base):
    """One message the clinic wanted to send.

    `status` records what really happened. `simulado` means no provider was
    configured and nothing left the server — it is kept separate from
    `enviado` so nobody reads a demo as a delivery."""

    __tablename__ = "outbound_messages"

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True, index=True
    )
    reminder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointment_reminders.id"), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    to_address: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    provider: Mapped[str | None] = mapped_column(String(40))
    provider_message_id: Mapped[str | None] = mapped_column(String(160))
    error: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
