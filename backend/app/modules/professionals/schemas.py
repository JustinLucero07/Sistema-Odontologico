import uuid

from pydantic import BaseModel, Field


class SpecialtyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class SpecialtyOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class ProfessionalCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    specialty_id: uuid.UUID | None = None
    license_number: str | None = None
    color_hex: str = "#0F6FFF"
    user_id: uuid.UUID | None = None


class ProfessionalUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    specialty_id: uuid.UUID | None = None
    license_number: str | None = None
    color_hex: str | None = None
    is_active: bool | None = None


class ProfessionalOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    specialty_id: uuid.UUID | None
    license_number: str | None
    color_hex: str
    is_active: bool

    model_config = {"from_attributes": True}
