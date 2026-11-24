import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.orthodontics.constants import (
    CASE_STATUS_CODES,
    DOC_FIELDS,
    DOC_STATUS_CODES,
    MAX_CONTROLS,
    TAD_CODES,
)
from app.modules.payments.schemas import PaymentCreate

MAX_AMOUNT = Decimal("1000000")


def _texto(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


class CaseFields(BaseModel):
    professional_id: uuid.UUID | None = None
    status: str | None = None
    stage: str | None = Field(default=None, max_length=120)
    needs_review: bool | None = None
    has_tad: str | None = None
    appliance: str | None = Field(default=None, max_length=60)
    started_on: date | None = None
    estimated_months: int | None = Field(default=None, ge=1, le=120)
    agreed_total: Decimal | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    special_attention: bool | None = None
    special_attention_note: str | None = Field(default=None, max_length=300)
    doc_xrays: str | None = None
    doc_photos: str | None = None
    doc_models: str | None = None
    doc_folder: str | None = None
    doc_notes: dict[str, str] | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v is not None and v not in CASE_STATUS_CODES:
            raise ValueError("Estado de ortodoncia no válido")
        return v

    @field_validator("has_tad")
    @classmethod
    def _tad(cls, v):
        if v is not None and v not in TAD_CODES:
            raise ValueError("Valor de TAD no válido")
        return v

    @field_validator("doc_xrays", "doc_photos", "doc_models", "doc_folder")
    @classmethod
    def _doc(cls, v):
        if v is not None and v not in DOC_STATUS_CODES:
            raise ValueError("Estado de documento no válido")
        return v

    @field_validator("doc_notes")
    @classmethod
    def _notas(cls, v):
        if v is None:
            return v
        validos = {f for f, _ in DOC_FIELDS}
        return {k: (t or "").strip()[:200] for k, t in v.items() if k in validos and (t or "").strip()}

    @field_validator("stage", "appliance", "special_attention_note", "notes")
    @classmethod
    def _limpiar(cls, v):
        return _texto(v)


class CaseCreate(CaseFields):
    patient_id: uuid.UUID


class CaseUpdate(CaseFields):
    pass


class ControlFields(BaseModel):
    planned_on: date | None = None
    attended_on: date | None = None
    planning: str | None = Field(default=None, max_length=2000)
    arches: str | None = Field(default=None, max_length=500)
    elastics: str | None = Field(default=None, max_length=500)
    tads: str | None = Field(default=None, max_length=500)
    due_on: date | None = None
    amount: Decimal | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("planning", "arches", "elastics", "tads", "notes")
    @classmethod
    def _limpiar(cls, v):
        return _texto(v)


class ControlCreate(ControlFields):
    pass


class ControlUpdate(ControlFields):
    pass


class ControlsGenerate(BaseModel):
    """Crea varias cuotas de una vez: «36 cuotas de $30 desde el 16/07»."""

    count: int = Field(ge=1, le=MAX_CONTROLS)
    first_on: date
    amount: Decimal = Field(ge=0, le=MAX_AMOUNT)
    every_days: int | None = Field(default=None, ge=7, le=120)  # None = mensual


class ControlPayment(PaymentCreate):
    """Abono a una cuota. El cargo lo pone el sistema (el del tratamiento)."""


class PaymentLine(BaseModel):
    id: uuid.UUID
    amount: Decimal
    method: str
    reference: str | None
    received_on: date
    notes: str | None
    voided_at: datetime | None = None
    void_reason: str | None = None

    model_config = {"from_attributes": True}


class ControlOut(BaseModel):
    id: uuid.UUID
    number: int
    planned_on: date | None
    attended_on: date | None
    planning: str | None
    arches: str | None
    elastics: str | None
    tads: str | None
    due_on: date | None
    amount: Decimal
    notes: str | None
    paid: Decimal
    balance: Decimal
    status: str  # pendiente | parcial | pagada | vencida | sin_valor
    payments: list[PaymentLine]


class PatientMini(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    national_id: str | None
    phone: str | None
    whatsapp: str | None


class CaseOut(BaseModel):
    id: uuid.UUID
    number: int
    code: str
    patient: PatientMini
    professional_id: uuid.UUID | None
    professional_name: str | None
    charge_id: uuid.UUID | None
    status: str
    stage: str | None
    needs_review: bool
    has_tad: str
    appliance: str | None
    started_on: date | None
    estimated_months: int | None
    agreed_total: Decimal
    special_attention: bool
    special_attention_note: str | None
    doc_xrays: str
    doc_photos: str
    doc_models: str
    doc_folder: str
    doc_notes: dict[str, str]
    notes: str | None
    # Calculado
    paid: Decimal
    balance: Decimal
    controls_total: Decimal
    difference: Decimal
    controls_count: int
    controls_paid: int
    last_control_on: date | None
    next_control_on: date | None
    next_control_overdue: bool
    docs_pending: int


class CaseDetail(CaseOut):
    controls: list[ControlOut]
    unassigned_paid: Decimal  # abonos al tratamiento sin cuota asignada


class CaseList(BaseModel):
    items: list[CaseOut]
    total: int
    active: int
    inactive: int
