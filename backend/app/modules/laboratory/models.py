import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class Laboratory(UUIDPKMixin, TenantMixin, Base):
    """A dental laboratory the clinic sends work to."""

    __tablename__ = "laboratories"
    __table_args__ = (UniqueConstraint("clinic_id", "name", name="uq_laboratory_name"),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(300))
    # Typical turnaround, used to propose a due date rather than to enforce one.
    default_turnaround_days: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)


class LabOrder(UUIDPKMixin, TenantMixin, Base):
    """A case sent out to a laboratory.

    The status history lives in its own table rather than as a single column,
    because "when did this crown come back, and how long did it sit at the lab"
    is the question a clinic actually asks — and a lone current-status column
    cannot answer it."""

    __tablename__ = "lab_orders"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    laboratory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratories.id"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True
    )
    treatment_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_plan_items.id"), nullable=True
    )

    work_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    fdi_numbers: Mapped[list[str] | None] = mapped_column(ARRAY(String(3)))
    shade: Mapped[str | None] = mapped_column(String(40))
    material: Mapped[str | None] = mapped_column(String(120))

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="borrador")
    sent_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
    received_on: Mapped[date | None] = mapped_column(Date)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    laboratory: Mapped["Laboratory"] = relationship()
    events: Mapped[list["LabOrderEvent"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="LabOrderEvent.created_at"
    )


class LabOrderEvent(UUIDPKMixin, TenantMixin, Base):
    """One step in a case's life. Append-only."""

    __tablename__ = "lab_order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    order: Mapped["LabOrder"] = relationship(back_populates="events")
