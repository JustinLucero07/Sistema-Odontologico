import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.credits.constants import FREQUENCY_DAYS, MAX_INSTALLMENTS, MAX_MONTHLY_RATE
from app.modules.payments.constants import MAX_AMOUNT, METHODS_REQUIRING_REFERENCE, PAYMENT_METHOD_CODES, money


class _Terms(BaseModel):
    installment_count: int = Field(ge=1, le=MAX_INSTALLMENTS)
    frequency: str = "mensual"
    first_due_on: date

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str) -> str:
        if value not in FREQUENCY_DAYS:
            raise ValueError(f"Frecuencia inválida: {value}")
        return value


class CreditCreate(_Terms):
    charge_id: uuid.UUID
    monthly_rate: Decimal = Field(ge=0, le=MAX_MONTHLY_RATE, default=Decimal("0"))
    down_payment: Decimal = Field(ge=0, le=MAX_AMOUNT, default=Decimal("0"))
    down_payment_method: str = "efectivo"
    down_payment_reference: str | None = None
    guarantor_name: str | None = Field(default=None, max_length=200)
    guarantor_id_number: str | None = Field(default=None, max_length=30)
    guarantor_phone: str | None = Field(default=None, max_length=40)
    notes: str | None = None

    @field_validator("down_payment")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return money(value)

    @field_validator("down_payment_method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        if value not in PAYMENT_METHOD_CODES:
            raise ValueError(f"Medio de pago inválido: {value}")
        return value


class CreditUpdate(BaseModel):
    guarantor_name: str | None = Field(default=None, max_length=200)
    guarantor_id_number: str | None = Field(default=None, max_length=30)
    guarantor_phone: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class CreditRestructure(_Terms):
    """Refinanciar: el saldo pendiente se reparte en un calendario nuevo, sin
    intereses adicionales. Las cuotas ya pagadas no cambian."""


class CreditPayment(BaseModel):
    amount: Decimal = Field(gt=0, le=MAX_AMOUNT)
    method: str
    reference: str | None = Field(default=None, max_length=120)
    received_on: date | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return money(value)

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        if value not in PAYMENT_METHOD_CODES:
            raise ValueError(f"Medio de pago inválido: {value}")
        return value

    def model_post_init(self, _context: object) -> None:
        if self.method in METHODS_REQUIRING_REFERENCE and not (self.reference or "").strip():
            raise ValueError("Este medio de pago requiere número de referencia")


class PreviewRow(BaseModel):
    number: int
    due_on: date
    principal: Decimal
    interest: Decimal
    amount: Decimal


class Preview(BaseModel):
    rows: list[PreviewRow]
    total: Decimal
    total_interest: Decimal
    installment_amount: Decimal
    annual_rate: Decimal


class InstallmentRow(BaseModel):
    number: int
    due_on: date
    principal: Decimal
    interest: Decimal
    amount: Decimal
    paid: Decimal
    pending: Decimal
    status: str  # pagada | parcial | pendiente | vencida
    days_late: int


class CreditPaymentRow(BaseModel):
    group_id: uuid.UUID
    received_on: date
    amount: Decimal
    method: str
    method_label: str
    reference: str | None
    voided_at: datetime | None
    void_reason: str | None
    payment_ids: list[uuid.UUID]


class CreditOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    patient_phone: str | None
    charge_id: uuid.UUID
    charge_description: str
    interest_charge_id: uuid.UUID | None
    down_payment: Decimal
    principal: Decimal
    monthly_rate: Decimal
    frequency: str
    frequency_label: str
    installment_count: int
    first_due_on: date
    total: Decimal
    total_interest: Decimal
    paid: Decimal
    pending: Decimal
    overdue: Decimal
    days_late: int
    next_due_on: date | None
    next_amount: Decimal | None
    status: str  # al_dia | vencido | pagado | anulado
    guarantor_name: str | None
    guarantor_id_number: str | None
    guarantor_phone: str | None
    notes: str | None
    created_at: datetime
    voided_at: datetime | None
    void_reason: str | None
    communications_allowed: bool


class CreditDetail(CreditOut):
    installments: list[InstallmentRow]
    payments: list[CreditPaymentRow]


class CreditSummary(BaseModel):
    active_count: int
    overdue_count: int
    outstanding: Decimal
    overdue_amount: Decimal
    collected_this_month: Decimal
