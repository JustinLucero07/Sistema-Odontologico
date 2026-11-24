import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class Charge(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "charges"
    __table_args__ = (
        # One charge per budget: accepting a budget twice must not bill twice.
        UniqueConstraint("budget_id", name="uq_charge_budget"),
        CheckConstraint("amount > 0", name="ck_charge_amount_positive"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True, index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text)

    payments: Mapped[list["Payment"]] = relationship(back_populates="charge")
    installments: Mapped[list["Installment"]] = relationship(
        back_populates="charge", cascade="all, delete-orphan", order_by="Installment.number"
    )


class Payment(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        Index("ix_payments_clinic_received", "clinic_id", "received_on"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    charge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("charges.id"), nullable=True, index=True
    )
    credit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credits.id"), nullable=True, index=True
    )
    split_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ortho_control_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ortho_controls.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cash_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cash_sessions.id"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text)

    charge: Mapped["Charge | None"] = relationship(back_populates="payments")
    cash_session: Mapped["CashSession | None"] = relationship(back_populates="payments")


class Installment(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "installments"
    __table_args__ = (
        UniqueConstraint("charge_id", "number", name="uq_installment_number"),
        CheckConstraint("amount > 0", name="ck_installment_amount_positive"),
    )

    charge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("charges.id"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    charge: Mapped["Charge"] = relationship(back_populates="installments")


class CashSession(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "cash_sessions"

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    opening_float: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    counted_cash: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_cash: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    payments: Mapped[list["Payment"]] = relationship(back_populates="cash_session")

    @property
    def is_open(self) -> bool:
        return self.closed_at is None
