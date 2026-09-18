import uuid

from pydantic import BaseModel, Field


class TreatmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    default_price: float = Field(ge=0, default=0)


class TreatmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_price: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class TreatmentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    default_price: float
    is_active: bool

    model_config = {"from_attributes": True}
