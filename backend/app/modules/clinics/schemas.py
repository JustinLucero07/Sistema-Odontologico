import uuid

from pydantic import BaseModel, Field


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
    currency: str | None = None


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


class OperatoryOut(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}
