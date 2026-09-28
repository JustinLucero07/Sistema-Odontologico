import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin
from app.shared.voiding import VoidableMixin


class Expense(UUIDPKMixin, TenantMixin, VoidableMixin, Base):
    """Un egreso: dinero que salió de la clínica.

    Como los cobros, un gasto no se borra: si se registró mal se anula con
    motivo y se registra el correcto. Así el arqueo de un día ya cerrado sigue
    cuadrando con lo que se vio ese día."""

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
    # Número de la factura o comprobante del proveedor: es lo que respalda el
    # gasto ante el SRI y lo que pide el contador.
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
