import uuid

from pydantic import BaseModel, Field, field_validator

# Códigos de IVA del SRI que admite un tratamiento (ver invoicing.constants).
VAT_CODES = {"0", "4", "5", "6", "7"}


def _iva(v: str | None) -> str | None:
    if v is not None and v not in VAT_CODES:
        raise ValueError("Código de IVA inválido")
    return v


class TreatmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    default_price: float = Field(ge=0, default=0)
    vat_code: str = "0"

    @field_validator("vat_code")
    @classmethod
    def _v(cls, v: str | None) -> str | None:
        return _iva(v)


class TreatmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_price: float | None = Field(default=None, ge=0)
    is_active: bool | None = None
    vat_code: str | None = None

    @field_validator("vat_code")
    @classmethod
    def _v(cls, v: str | None) -> str | None:
        return _iva(v)


class TreatmentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    default_price: float
    is_active: bool
    vat_code: str = "0"

    model_config = {"from_attributes": True}
