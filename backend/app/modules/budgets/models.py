import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Budget(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "budgets"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    treatment_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("treatment_plans.id"), nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="borrador")
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["BudgetItem"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan", order_by="BudgetItem.created_at"
    )

    @property
    def subtotal(self) -> float:
        return sum(item.net_price * item.quantity for item in self.items)

    @property
    def tax_amount(self) -> float:
        return self.subtotal * float(self.tax_rate) / 100

    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount


class BudgetItem(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "budget_items"

    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False, index=True)
    treatment_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_plan_items.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    budget: Mapped["Budget"] = relationship(back_populates="items")

    @property
    def net_price(self) -> float:
        return float(self.price) - float(self.discount)
