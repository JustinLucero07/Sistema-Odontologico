import re
import uuid

from pydantic import BaseModel, Field, field_validator

ACCOUNT_TYPES = {"ahorros", "corriente", "otra"}
MAX_QR = 900_000  # ~650 KB de imagen en base64


def _texto(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


class AccountFields(BaseModel):
    qr_data: str | None = None
    holder_name: str | None = Field(default=None, max_length=150)
    holder_id: str | None = Field(default=None, max_length=20)
    account_type: str | None = None
    account_number: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=300)
    is_active: bool | None = None

    @field_validator("holder_name", "holder_id", "account_number", "email", "note")
    @classmethod
    def _limpiar(cls, v):
        return _texto(v)

    @field_validator("account_type")
    @classmethod
    def _tipo(cls, v):
        v = _texto(v)
        if v is not None and v not in ACCOUNT_TYPES:
            raise ValueError("Tipo de cuenta no válido")
        return v

    @field_validator("qr_data")
    @classmethod
    def _qr(cls, v):
        if v in (None, ""):
            return None
        if not re.match(r"^data:image/(png|jpeg|webp);base64,", v):
            raise ValueError("El QR debe ser una imagen PNG, JPG o WebP")
        if len(v) > MAX_QR:
            raise ValueError("La imagen del QR es demasiado grande (máximo 650 KB)")
        return v


class AccountCreate(AccountFields):
    label: str = Field(min_length=1, max_length=80)

    def model_post_init(self, _context: object) -> None:
        if not (self.qr_data or self.account_number or self.email):
            raise ValueError("Agregue el código QR o los datos de la cuenta")


class AccountUpdate(AccountFields):
    label: str | None = Field(default=None, min_length=1, max_length=80)


class AccountOut(BaseModel):
    id: uuid.UUID
    label: str
    qr_data: str | None
    holder_name: str | None
    holder_id: str | None
    account_type: str | None
    account_number: str | None
    email: str | None
    note: str | None
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class Reorder(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
