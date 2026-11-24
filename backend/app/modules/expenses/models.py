import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin
from app.shared.voiding import VoidableMixin


class Expense(UUIDPKMixin, TenantMixin, VoidableMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        Index("ix_expenses_clinic_spent", "clinic_id", "spent_on"),
    )

    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True
    )
    supplier_name: Mapped[str | None] = mapped_column(String(160))
    receipt_number: Mapped[str | None] = mapped_column(String(80))
    # Si se pagó en efectivo con la caja abierta, sale de esa caja.
    cash_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cash_sessions.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecurringExpense(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "recurring_expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_recurring_expense_amount_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 28", name="ck_recurring_expense_day"),
    )

    description: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False, default="transferencia")
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supplier_name: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Último mes (AAAA-MM) en que se registró como egreso.
    last_registered_month: Mapped[str | None] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
