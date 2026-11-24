import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class Periodontogram(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "periodontograms"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_periodontogram_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("periodontograms.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    teeth: Mapped[list["PeriodontalTooth"]] = relationship(
        back_populates="periodontogram", cascade="all, delete-orphan"
    )
    measurements: Mapped[list["PeriodontalMeasurement"]] = relationship(
        back_populates="periodontogram", cascade="all, delete-orphan"
    )

    @property
    def type(self) -> str:
        return "initial" if self.previous_periodontogram_id is None else "followup"


class PeriodontalTooth(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "periodontal_teeth"
    __table_args__ = (UniqueConstraint("periodontogram_id", "fdi_number", name="uq_periodontal_tooth"),)

    periodontogram_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("periodontograms.id"), nullable=False, index=True
    )
    fdi_number: Mapped[str] = mapped_column(String(3), nullable=False)
    absent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    implant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mobility: Mapped[int | None] = mapped_column(SmallInteger)
    furcation: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)

    periodontogram: Mapped["Periodontogram"] = relationship(back_populates="teeth")


class PeriodontalMeasurement(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "periodontal_measurements"
    __table_args__ = (
        UniqueConstraint(
            "periodontogram_id", "fdi_number", "site", name="uq_periodontal_measurement_site"
        ),
    )

    periodontogram_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("periodontograms.id"), nullable=False, index=True
    )
    fdi_number: Mapped[str] = mapped_column(String(3), nullable=False)
    site: Mapped[str] = mapped_column(String(24), nullable=False)
    probing_depth: Mapped[int | None] = mapped_column(Integer)
    recession: Mapped[int | None] = mapped_column(Integer)
    bleeding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suppuration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plaque: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    periodontogram: Mapped["Periodontogram"] = relationship(back_populates="measurements")
