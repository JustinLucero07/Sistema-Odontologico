import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.invoicing.constants import AMBIENTES, FORMAS_PAGO, IVA, TIPOS_IDENTIFICACION


class SettingsOut(BaseModel):
    environment: str
    send_email: bool
    retention_agent: str | None
    has_certificate: bool
    certificate_subject: str | None
    certificate_valid_until: datetime | None
    certificate_expired: bool
    email_configured: bool
    next_invoice_number: int
    establishment: str
    emission_point: str
    # Lo que falta para poder emitir (vacío = listo).
    missing: list[str]


class SettingsUpdate(BaseModel):
    environment: str | None = None
    send_email: bool | None = None
    retention_agent: str | None = None
    next_invoice_number: int | None = Field(default=None, ge=1, le=999999999)

    @field_validator("environment")
    @classmethod
    def ambiente(cls, v: str | None) -> str | None:
        if v is not None and v not in AMBIENTES:
            raise ValueError("Ambiente inválido (1 pruebas, 2 producción)")
        return v


class Buyer(BaseModel):
    id_type: str
    id_number: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=300)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=50)

    @field_validator("id_type")
    @classmethod
    def tipo(cls, v: str) -> str:
        if v not in TIPOS_IDENTIFICACION:
            raise ValueError("Tipo de identificación inválido")
        return v


class ItemIn(BaseModel):
    """Una línea: o un cargo de la cuenta del paciente (charge_id), o un
    concepto escrito a mano."""

    charge_id: uuid.UUID | None = None
    code: str | None = Field(default=None, max_length=25)
    description: str | None = Field(default=None, max_length=300)
    quantity: Decimal = Field(default=Decimal(1), gt=0, le=Decimal("999999"))
    # Precio por unidad. Si price_includes_vat, ya trae el IVA incluido y se
    # separa al facturar (lo habitual en un consultorio: «la limpieza cuesta 40»).
    unit_price: Decimal | None = Field(default=None, ge=0, le=Decimal("9999999"))
    price_includes_vat: bool = True
    discount: Decimal = Field(default=Decimal(0), ge=0)
    vat_code: str = "0"

    @field_validator("vat_code")
    @classmethod
    def iva(cls, v: str) -> str:
        if v not in IVA:
            raise ValueError("Código de IVA inválido")
        return v


class InvoiceCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    # Sin comprador: se toma de la ficha del paciente; sin paciente, consumidor final.
    buyer: Buyer | None = None
    items: list[ItemIn] = Field(min_length=1, max_length=200)
    payment_method: str = "01"
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("payment_method")
    @classmethod
    def forma(cls, v: str) -> str:
        if v not in FORMAS_PAGO:
            raise ValueError("Forma de pago inválida")
        return v


class CreditNoteCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    # Sin monto: anula la factura completa. Con monto (IVA incluido): parcial.
    amount: Decimal | None = Field(default=None, gt=0)


class DiscardRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class EmailRequest(BaseModel):
    email: EmailStr | None = None


class LineOut(BaseModel):
    id: uuid.UUID
    charge_id: uuid.UUID | None
    code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    subtotal: Decimal
    vat_code: str
    vat_rate: Decimal
    vat: Decimal

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: uuid.UUID
    doc_type: str
    number: str
    patient_id: uuid.UUID | None
    modified_invoice_id: uuid.UUID | None
    reason: str | None
    environment: str
    access_key: str
    issue_date: date
    buyer_id_type: str
    buyer_id: str
    buyer_name: str
    buyer_email: str | None
    buyer_address: str | None
    buyer_phone: str | None
    payment_method: str
    subtotal: Decimal
    discount: Decimal
    vat: Decimal
    total: Decimal
    notes: str | None
    status: str
    sri_messages: list
    authorized_at: datetime | None
    attempts: int
    next_attempt_at: datetime | None
    last_error: str | None
    emailed_at: datetime | None
    discarded_at: datetime | None
    discard_reason: str | None
    created_at: datetime
    lines: list[LineOut] = []
    # Notas de crédito emitidas sobre esta factura (vigentes) y su total.
    credited: Decimal = Decimal(0)

    model_config = {"from_attributes": True}


class InvoiceableCharge(BaseModel):
    id: uuid.UUID
    description: str
    amount: Decimal
    issued_on: date
