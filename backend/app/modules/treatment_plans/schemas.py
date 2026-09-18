import uuid
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.modules.treatment_plans.constants import TREATMENT_PLAN_ITEM_STATUS_CODES


class TreatmentPlanItemCreate(BaseModel):
    treatment_id: uuid.UUID
    diagnosis_id: uuid.UUID | None = None
    professional_id: uuid.UUID | None = None
    fdi_number: str | None = None
    surface: str | None = None
    price: float = Field(ge=0, default=0)
    discount: float = Field(ge=0, default=0)
    status: str = "propuesto"
    estimated_date: date | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in TREATMENT_PLAN_ITEM_STATUS_CODES:
            raise ValueError(f"Estado inválido: {value}")
        return value


class TreatmentPlanItemUpdate(BaseModel):
    diagnosis_id: uuid.UUID | None = None
    professional_id: uuid.UUID | None = None
    fdi_number: str | None = None
    surface: str | None = None
    price: float | None = Field(default=None, ge=0)
    discount: float | None = Field(default=None, ge=0)
    status: str | None = None
    estimated_date: date | None = None
    completed_date: date | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in TREATMENT_PLAN_ITEM_STATUS_CODES:
            raise ValueError(f"Estado inválido: {value}")
        return value


class TreatmentPlanItemOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    treatment_id: uuid.UUID
    treatment_name: str
    diagnosis_id: uuid.UUID | None
    professional_id: uuid.UUID | None
    fdi_number: str | None
    surface: str | None
    price: float
    discount: float
    net_price: float
    status: str
    estimated_date: date | None
    completed_date: date | None
    notes: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_item(cls, item) -> "TreatmentPlanItemOut":
        return cls(
            id=item.id, plan_id=item.plan_id, treatment_id=item.treatment_id,
            treatment_name=item.treatment.name, diagnosis_id=item.diagnosis_id,
            professional_id=item.professional_id, fdi_number=item.fdi_number, surface=item.surface,
            price=float(item.price), discount=float(item.discount), net_price=item.net_price,
            status=item.status, estimated_date=item.estimated_date, completed_date=item.completed_date,
            notes=item.notes,
        )


class TreatmentPlanCreate(BaseModel):
    title: str = Field(default="Plan de tratamiento", max_length=200)
    notes: str | None = None
    items: list[TreatmentPlanItemCreate] = Field(default_factory=list)


class TreatmentPlanOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    created_by_id: uuid.UUID | None
    title: str
    notes: str | None
    items: list[TreatmentPlanItemOut]
    progress_percent: float
    total_price: float

    model_config = {"from_attributes": True}

    @classmethod
    def from_plan(cls, plan) -> "TreatmentPlanOut":
        from app.modules.treatment_plans.constants import COMPLETED_STATUSES, VOID_STATUSES

        counted_items = [i for i in plan.items if i.status not in VOID_STATUSES]
        completed = sum(1 for i in counted_items if i.status in COMPLETED_STATUSES)
        progress = (completed / len(counted_items) * 100) if counted_items else 0.0

        return cls(
            id=plan.id, patient_id=plan.patient_id, created_by_id=plan.created_by_id,
            title=plan.title, notes=plan.notes,
            items=[TreatmentPlanItemOut.from_item(i) for i in plan.items],
            progress_percent=round(progress, 1),
            total_price=sum(i.net_price for i in plan.items),
        )
