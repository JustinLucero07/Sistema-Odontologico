import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, BigInteger, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin

IMAGE_TYPES = [
    ("panoramica", "Radiografía panorámica"),
    ("periapical", "Radiografía periapical"),
    ("bitewing", "Radiografía bitewing (aleta de mordida)"),
    ("lateral", "Telerradiografía lateral"),
    ("oclusal", "Radiografía oclusal"),
    ("tomografia", "Tomografía (CBCT)"),
    ("foto_intraoral", "Fotografía intraoral"),
    ("foto_extraoral", "Fotografía extraoral"),
    ("otro", "Otra imagen"),
]
IMAGE_TYPE_CODES = {code for code, _ in IMAGE_TYPES}

TOOTH_SCOPED_TYPES = {"periapical", "bitewing", "oclusal"}


class ClinicalImage(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "clinical_images"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    image_type: Mapped[str] = mapped_column(String(40), nullable=False, default="otro")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    taken_on: Mapped[date | None] = mapped_column(Date)
    fdi_numbers: Mapped[list[str] | None] = mapped_column(ARRAY(String(3)))

    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    archived_reason: Mapped[str | None] = mapped_column(Text)
