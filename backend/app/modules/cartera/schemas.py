import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.expenses.constants import EXPENSE_CATEGORY_CODES
from app.modules.payments.constants import PAYMENT_METHOD_CODES, money


class PatientBalance(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    national_id: str | None
    phone: str | None
    total_charged: Decimal
    total_paid: Decimal
    balance: Decimal          # > 0 debe · = 0 saldado · < 0 saldo a favor
    status: str               # debe | saldado | a_favor
    open_charges: int
    oldest_pending_on: date | None
    days_pending: int | None
    last_payment_on: date | None
    in_credit: bool


class ChargeRow(BaseModel):
    charge_id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    description: str
    issued_on: date
    amount: Decimal
    paid: Decimal
    pending: Decimal
    status: str               # pendiente | parcial | pagada
    in_credit: bool
    days_open: int


class TreatmentRow(BaseModel):
    item_id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    plan_title: str
    treatment: str
    fdi_number: str | None
    status: str
    net_price: Decimal
    professional_name: str | None
    estimated_date: date | None
    completed_date: date | None


class PortfolioSummary(BaseModel):
    total_charged: Decimal
    total_paid: Decimal
    receivable: Decimal
    credit_balance: Decimal   # saldos a favor de pacientes
    patients_owing: int
    patients_settled: int
    patients_credit: int
    open_charges: int
    treatments_in_progress: int
    treatments_in_progress_value: Decimal
    treatments_planned: int
    treatments_planned_value: Decimal
    collection_rate: float | None   # pagado / cargado


class Portfolio(BaseModel):
    summary: PortfolioSummary
    patients: list[PatientBalance]
    charges: list[ChargeRow]
    treatments: list[TreatmentRow]


class ProjectionItem(BaseModel):
    on: date
    kind: str                 # cuota_credito | cuota_cargo | gasto_fijo
    label: str
    patient_name: str | None
    amount: Decimal


class Projection(BaseModel):
    days: int
    expected_in: Decimal
    expected_out: Decimal
    net: Decimal
    overdue_in: Decimal
    items: list[ProjectionItem]


class RecurringIn(BaseModel):
    description: str = Field(min_length=2, max_length=300)
    category: str
    amount: Decimal = Field(gt=0)
    method: str = "transferencia"
    day_of_month: int = Field(default=1, ge=1, le=28)
    supplier_name: str | None = None
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def _cat(cls, v):
        if v not in EXPENSE_CATEGORY_CODES:
            raise ValueError("Categoría no válida")
        return v

    @field_validator("method")
    @classmethod
    def _met(cls, v):
        if v not in PAYMENT_METHOD_CODES:
            raise ValueError("Medio de pago no válido")
        return v

    @field_validator("amount")
    @classmethod
    def _q(cls, v):
        return money(v)


class RecurringOut(RecurringIn):
    id: uuid.UUID
    category_label: str
    method_label: str
    last_registered_month: str | None
    due_this_month: bool      # activo y aún no registrado este mes
    due_on: date


class RegisterRecurring(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    spent_on: date | None = None
