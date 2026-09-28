import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.expenses.constants import EXPENSE_CATEGORY_CODES
from app.modules.payments.constants import MAX_AMOUNT, PAYMENT_METHOD_CODES, money


class _ExpenseFields(BaseModel):
    spent_on: date
    category: str
    description: str = Field(min_length=1, max_length=300)
    supplier_id: uuid.UUID | None = None
    supplier_name: str | None = Field(default=None, max_length=160)
    receipt_number: str | None = Field(default=None, max_length=80)
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in EXPENSE_CATEGORY_CODES:
            raise ValueError(f"Categoría inválida: {value}")
        return value


class ExpenseCreate(_ExpenseFields):
    amount: Decimal = Field(gt=0, le=MAX_AMOUNT)
    method: str = "efectivo"

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        if value not in PAYMENT_METHOD_CODES:
            raise ValueError(f"Medio de pago inválido: {value}")
        return value

    @field_validator("amount")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return money(value)


class ExpenseUpdate(_ExpenseFields):
    """El importe y el medio no se editan: cambiar el dinero de un gasto ya
    registrado descuadraría la caja de ese día. Se anula y se registra bien."""


class ExpenseOut(BaseModel):
    id: uuid.UUID
    spent_on: date
    category: str
    category_label: str
    description: str
    amount: Decimal
    method: str
    method_label: str
    supplier_id: uuid.UUID | None
    supplier_name: str | None
    receipt_number: str | None
    cash_session_id: uuid.UUID | None
    notes: str | None
    created_by_name: str | None
    created_at: datetime
    voided_at: datetime | None
    void_reason: str | None


class Breakdown(BaseModel):
    code: str
    label: str
    total: Decimal
    count: int


class MonthRow(BaseModel):
    month: str
    income: Decimal
    expenses: Decimal
    net: Decimal


class FinanceSummary(BaseModel):
    date_from: date
    date_to: date
    # Ventas: servicios cargados a pacientes (lo facturado), cobrado o no.
    sales: Decimal
    # Ingresos: dinero efectivamente cobrado.
    income: Decimal
    expenses: Decimal
    # Resultado de caja del periodo: lo cobrado menos lo gastado.
    net: Decimal
    receivables: Decimal
    income_by_method: list[Breakdown]
    expenses_by_category: list[Breakdown]
    monthly: list[MonthRow]


class PaymentRow(BaseModel):
    id: uuid.UUID
    received_on: date
    patient_id: uuid.UUID
    patient_name: str
    concept: str | None
    amount: Decimal
    method: str
    method_label: str
    reference: str | None
    received_by_name: str | None
    voided_at: datetime | None
    void_reason: str | None


class CashSessionRow(BaseModel):
    id: uuid.UUID
    opened_at: datetime
    closed_at: datetime | None
    opened_by_name: str | None
    closed_by_name: str | None
    opening_float: Decimal
    cash_in: Decimal
    cash_out: Decimal
    expected_cash: Decimal
    counted_cash: Decimal | None
    difference: Decimal | None
    notes: str | None
