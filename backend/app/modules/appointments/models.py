import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.patients.models import Patient
from app.modules.professionals.models import Professional
from app.modules.treatments.models import Treatment
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Appointment(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    """A booked slot in a professional's calendar.

    Overlaps are rejected by exclusion constraints on the table itself (see the
    Alembic migration), not only by the service layer — two receptionists
    booking the same slot at the same instant must not both succeed."""

    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=False, index=True)
    operatory_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("operatories.id"), nullable=True)
    treatment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("treatments.id"), nullable=True)
    # Links the calendar back to the treatment plan, so a booked appointment is
    # not an island: it can point at the exact plan item it is meant to resolve.
    treatment_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_plan_items.id"), nullable=True
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="programada")
    color_hex: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    reminders: Mapped[list["AppointmentReminder"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )
    patient: Mapped["Patient"] = relationship()
    professional: Mapped["Professional"] = relationship()
    treatment: Mapped["Treatment | None"] = relationship()

    @property
    def duration_minutes(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds() // 60)


class AppointmentReminder(UUIDPKMixin, TenantMixin, Base):
    """A reminder scheduled for an appointment.

    Nothing here sends anything: it records *what* should go out and *when*, so
    the messaging integrations added in a later phase only have to pick up rows
    that are due. Keeping the schedule in the database means a reminder survives
    a restart and can be audited after the fact."""

    __tablename__ = "appointment_reminders"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    appointment: Mapped["Appointment"] = relationship(back_populates="reminders")
