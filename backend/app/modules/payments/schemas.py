import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.payments.constants import (
    MAX_AMOUNT,
    METHODS_REQUIRING_REFERENCE,
    PAYMENT_METHOD_CODES,
    money,
)


class ChargeCreate(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(gt=0, le=MAX_AMOUNT)
    issued_on: date | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return money(value)


class InstallmentOut(BaseModel):
    id: uuid.UUID
    number: int
    due_on: date
    amount: Decimal

    model_config = {"from_attributes": True}


class InstallmentStatus(BaseModel):
    """A schedule row plus how much of it the payments so far actually cover."""

    number: int
    due_on: date
    amount: Decimal
    paid: Decimal
    pending: Decimal
    status: str  # pagada | parcial | pendiente | vencida


class InstallmentPlanCreate(BaseModel):
    count: int = Field(ge=2, le=36)
    first_due_on: date
    # Days between instalments; 30 is monthly in practice for a clinic.
    every_days: int = Field(ge=7, le=90, default=30)


class ChargeOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    budget_id: uuid.UUID | None
    description: str
    amount: Decimal
    issued_on: date
    created_at: datetime
    notes: str | None
    voided_at: datetime | None
    void_reason: str | None
    paid: Decimal
    pending: Decimal
    status: str  # pendiente | parcial | pagada | anulada
    installments: list[InstallmentStatus]


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, le=MAX_AMOUNT)
    method: str
    charge_id: uuid.UUID | None = None
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

    @field_validator("reference")
    @classmethod
    def strip_reference(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    def model_post_init(self, _context: object) -> None:
        # A card or transfer without its reference number cannot be matched
        # against the bank statement later, which is the whole point of
        # recording it.
        if self.method in METHODS_REQUIRING_REFERENCE and not self.reference:
            raise ValueError("Este medio de pago requiere número de referencia")


class PaymentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    charge_id: uuid.UUID | None
    cash_session_id: uuid.UUID | None
    amount: Decimal
    method: str
    reference: str | None
    received_on: date
    received_by_id: uuid.UUID | None
    created_at: datetime
    notes: str | None
    voided_at: datetime | None
    void_reason: str | None

    model_config = {"from_attributes": True}


class VoidRequest(BaseModel):
    """Voiding demands a reason: without one the statement records that money
    moved and then un-moved, with nothing to explain it to an auditor."""

    reason: str = Field(min_length=3)


class AccountStatement(BaseModel):
    patient_id: uuid.UUID
    total_charged: Decimal
    total_paid: Decimal
    balance: Decimal
    # Money received that is not tied to any charge yet.
    unallocated: Decimal
    overdue_amount: Decimal
    charges: list[ChargeOut]
    payments: list[PaymentOut]


class CashSessionOut(BaseModel):
    id: uuid.UUID
    opened_at: datetime
    opened_by_id: uuid.UUID | None
    opening_float: Decimal
    closed_at: datetime | None
    closed_by_id: uuid.UUID | None
    counted_cash: Decimal | None
    expected_cash: Decimal | None
    difference: Decimal | None
    notes: str | None
    is_open: bool

    model_config = {"from_attributes": True}


class CashSessionOpen(BaseModel):
    opening_float: Decimal = Field(ge=0, le=MAX_AMOUNT, default=Decimal("0"))

    @field_validator("opening_float")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return money(value)


class CashSessionClose(BaseModel):
    counted_cash: Decimal = Field(ge=0, le=MAX_AMOUNT)
    notes: str | None = None

    @field_validator("counted_cash")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return money(value)


class MethodBreakdown(BaseModel):
    method: str
    label: str
    total: Decimal
    count: int


class DailyCashReport(BaseModel):
    day: date
    total: Decimal
    payment_count: int
    by_method: list[MethodBreakdown]
    voided_total: Decimal
    voided_count: int
