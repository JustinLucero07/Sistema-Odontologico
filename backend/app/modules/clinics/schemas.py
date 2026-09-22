import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class ClinicOut(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str | None
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    logo_url: str | None
    primary_color: str | None
    secondary_color: str | None
    timezone: str
    currency: str

    model_config = {"from_attributes": True}


class ClinicUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    timezone: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        # Los reportes cuentan los días en esta zona: una mal escrita los
        # desplazaría sin avisar, así que se rechaza al guardarla.
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"Zona horaria desconocida: {value}")
        return value


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = None
    is_main: bool = False


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    is_main: bool | None = None


class BranchOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    is_main: bool

    model_config = {"from_attributes": True}


class OperatoryCreate(BaseModel):
    branch_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)


class OperatoryUpdate(BaseModel):
    branch_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class OperatoryOut(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}
