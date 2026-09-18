import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.budgets.constants import BUDGET_STATUS_CODES


class BudgetItemCreate(BaseModel):
    treatment_plan_item_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=300)
    price: float = Field(ge=0, default=0)
    discount: float = Field(ge=0, default=0)
    quantity: int = Field(ge=1, default=1)


class BudgetItemOut(BaseModel):
    id: uuid.UUID
    treatment_plan_item_id: uuid.UUID | None
    description: str
    price: float
    discount: float
    quantity: int
    net_price: float

    model_config = {"from_attributes": True}

    @classmethod
    def from_item(cls, item) -> "BudgetItemOut":
        return cls(
            id=item.id, treatment_plan_item_id=item.treatment_plan_item_id, description=item.description,
            price=float(item.price), discount=float(item.discount), quantity=item.quantity,
            net_price=item.net_price,
        )


class BudgetCreate(BaseModel):
    treatment_plan_id: uuid.UUID
    tax_rate: float = Field(ge=0, le=100, default=0)
    notes: str | None = None
    # When omitted, the budget is auto-generated from all of the plan's items.
    items: list[BudgetItemCreate] | None = None


class BudgetStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in BUDGET_STATUS_CODES:
            raise ValueError(f"Estado inválido: {value}")
        return value


class BudgetOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    treatment_plan_id: uuid.UUID
    created_by_id: uuid.UUID | None
    created_at: datetime
    status: str
    tax_rate: float
    notes: str | None
    responded_at: datetime | None
    items: list[BudgetItemOut]
    subtotal: float
    tax_amount: float
    total: float

    model_config = {"from_attributes": True}

    @classmethod
    def from_budget(cls, budget) -> "BudgetOut":
        return cls(
            id=budget.id, patient_id=budget.patient_id, treatment_plan_id=budget.treatment_plan_id,
            created_by_id=budget.created_by_id, created_at=budget.created_at, status=budget.status,
            tax_rate=float(budget.tax_rate), notes=budget.notes, responded_at=budget.responded_at,
            items=[BudgetItemOut.from_item(i) for i in budget.items],
            subtotal=budget.subtotal, tax_amount=budget.tax_amount, total=budget.total,
        )
