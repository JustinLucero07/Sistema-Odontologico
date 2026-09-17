import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class Odontogram(UUIDPKMixin, TenantMixin, Base):
    """A snapshot of the patient's whole dental chart at a point in time.
    Never mutated after creation — a new edit always inserts a new row and
    links back via previous_odontogram_id, which is what makes comparing two
    dates and printing historical states possible without reconstruction."""

    __tablename__ = "odontograms"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    professional_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_odontogram_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("odontograms.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    conditions: Mapped[list["ToothCondition"]] = relationship(
        back_populates="odontogram", cascade="all, delete-orphan"
    )

    @property
    def type(self) -> str:
        return "initial" if self.previous_odontogram_id is None else "followup"


class ToothCondition(UUIDPKMixin, TenantMixin, Base):
    """One recorded condition on one surface of one tooth within a snapshot.
    A tooth/surface with no row is implicitly 'sano' — only deviations from
    healthy are stored."""

    __tablename__ = "tooth_conditions"

    odontogram_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("odontograms.id"), nullable=False, index=True)
    fdi_number: Mapped[str] = mapped_column(String(3), nullable=False)
    surface: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    odontogram: Mapped["Odontogram"] = relationship(back_populates="conditions")
