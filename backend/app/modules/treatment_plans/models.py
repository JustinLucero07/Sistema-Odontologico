import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.treatments.models import Treatment
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class TreatmentPlan(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "treatment_plans"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Plan de tratamiento")
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["TreatmentPlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="TreatmentPlanItem.created_at"
    )


class TreatmentPlanItem(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "treatment_plan_items"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("treatment_plans.id"), nullable=False, index=True)
    treatment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("treatments.id"), nullable=False)
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnoses.id"), nullable=True)
    professional_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=True)
    fdi_number: Mapped[str | None] = mapped_column(String(3))
    surface: Mapped[str | None] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="propuesto")
    estimated_date: Mapped[date | None] = mapped_column(Date)
    completed_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    plan: Mapped["TreatmentPlan"] = relationship(back_populates="items")
    treatment: Mapped["Treatment"] = relationship()

    @property
    def net_price(self) -> float:
        return float(self.price) - float(self.discount)
