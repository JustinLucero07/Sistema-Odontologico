import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin

DOCUMENT_TYPES = [
    ("consentimiento", "Consentimiento informado"),
    ("historia", "Historia clínica"),
    ("presupuesto", "Presupuesto"),
    ("receta", "Receta"),
    ("radiografia", "Radiografía"),
    ("informe", "Informe"),
    ("otro", "Documento"),
]
DOCUMENT_TYPE_CODES = {code for code, _ in DOCUMENT_TYPES}


class Document(UUIDPKMixin, TenantMixin, Base):
    """A file attached to a patient. The bytes live wherever the configured
    StorageProvider puts them; this row only keeps the key plus what a person
    needs to find the file again."""

    __tablename__ = "documents"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document_type: Mapped[str] = mapped_column(String(40), nullable=False, default="otro")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    # Un documento no se borra: se archiva con motivo y se puede recuperar.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    archived_reason: Mapped[str | None] = mapped_column(Text)
