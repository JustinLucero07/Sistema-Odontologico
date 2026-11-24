import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class OrthoCase(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "ortho_cases"
    __table_args__ = (
        UniqueConstraint("clinic_id", "number", name="uq_ortho_case_number"),
        CheckConstraint("agreed_total >= 0", name="ck_ortho_case_total"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True
    )
    charge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("charges.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")
    stage: Mapped[str | None] = mapped_column(String(120))
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_tad: Mapped[str] = mapped_column(String(15), nullable=False, default="por_confirmar")
    appliance: Mapped[str | None] = mapped_column(String(60))
    started_on: Mapped[date | None] = mapped_column(Date)
    estimated_months: Mapped[int | None] = mapped_column(Integer)
    agreed_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    special_attention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    special_attention_note: Mapped[str | None] = mapped_column(String(300))

    doc_xrays: Mapped[str] = mapped_column(String(15), nullable=False, default="por_revisar")
    doc_photos: Mapped[str] = mapped_column(String(15), nullable=False, default="por_revisar")
    doc_models: Mapped[str] = mapped_column(String(15), nullable=False, default="por_revisar")
    doc_folder: Mapped[str] = mapped_column(String(15), nullable=False, default="por_revisar")
    # Nota breve por documento: {"doc_xrays": "Panorámica 2026", ...}
    doc_notes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    notes: Mapped[str | None] = mapped_column(Text)

    controls: Mapped[list["OrthoControl"]] = relationship(
        back_populates="case", order_by="OrthoControl.number", cascade="all, delete-orphan"
    )


class OrthoControl(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "ortho_controls"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_ortho_control_amount"),)

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ortho_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_on: Mapped[date | None] = mapped_column(Date)
    attended_on: Mapped[date | None] = mapped_column(Date)
    planning: Mapped[str | None] = mapped_column(Text)
    arches: Mapped[str | None] = mapped_column(Text)
    elastics: Mapped[str | None] = mapped_column(Text)
    tads: Mapped[str | None] = mapped_column(Text)
    due_on: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    case: Mapped["OrthoCase"] = relationship(back_populates="controls")
