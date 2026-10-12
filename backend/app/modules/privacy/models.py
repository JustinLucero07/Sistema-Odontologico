import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class DataConsent(UUIDPKMixin, TenantMixin, Base):
    """Constancia de lo que se informó al paciente y de lo que autorizó.

    Solo se añaden filas: retirar una autorización es una fila nueva con
    granted=False, nunca una edición. Así queda la historia completa de qué se
    autorizó, cuándo, cómo y ante quién, que es lo que habría que demostrar."""

    __tablename__ = "data_consents"
    __table_args__ = (
        Index("ix_data_consents_patient_kind", "patient_id", "kind", text("recorded_at DESC")),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    # Quien firma cuando el paciente es menor o no puede hacerlo.
    signed_by_name: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataRightsRequest(UUIDPKMixin, TenantMixin, Base):
    """Solicitud de un titular para ejercer sus derechos (acceso, rectificación,
    eliminación…). Hay que poder demostrar que se respondió y cuándo."""

    __tablename__ = "data_rights_requests"

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    requester_name: Mapped[str] = mapped_column(String(200), nullable=False)
    requester_id_number: Mapped[str | None] = mapped_column(String(20))
    contact: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    response: Mapped[str | None] = mapped_column(Text)
    resolved_on: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
