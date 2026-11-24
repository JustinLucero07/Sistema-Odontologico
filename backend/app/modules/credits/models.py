import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin
from app.shared.voiding import VoidableMixin


class Credit(UUIDPKMixin, TenantMixin, VoidableMixin, Base):
    __tablename__ = "credits"
    __table_args__ = (
        CheckConstraint("principal > 0", name="ck_credit_principal_positive"),
        CheckConstraint("monthly_rate >= 0", name="ck_credit_rate_non_negative"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    # El cargo del tratamiento que se financia.
    charge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("charges.id"), nullable=False, index=True
    )
    interest_charge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("charges.id"), nullable=True
    )
    down_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    principal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monthly_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="mensual")
    installment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_due_on: Mapped[date] = mapped_column(Date, nullable=False)

    guarantor_name: Mapped[str | None] = mapped_column(String(200))
    guarantor_id_number: Mapped[str | None] = mapped_column(String(30))
    guarantor_phone: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    installments: Mapped[list["CreditInstallment"]] = relationship(
        back_populates="credit", order_by="CreditInstallment.number", cascade="all, delete-orphan"
    )


class CreditInstallment(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "credit_installments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_credit_installment_positive"),)

    credit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credits.id"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    principal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    interest: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    credit: Mapped["Credit"] = relationship(back_populates="installments")
