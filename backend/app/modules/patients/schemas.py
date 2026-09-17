import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    national_id: str | None = None
    birth_date: date | None = None
    sex: Literal["M", "F", "O"] | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    occupation: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    notes: str | None = None


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    national_id: str | None = None
    birth_date: date | None = None
    sex: Literal["M", "F", "O"] | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    occupation: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    photo_url: str | None = None
    notes: str | None = None


class PatientOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    national_id: str | None
    birth_date: date | None
    age: int | None
    sex: str | None
    phone: str | None
    whatsapp: str | None
    email: str | None
    address: str | None
    city: str | None
    occupation: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    photo_url: str | None
    notes: str | None

    model_config = {"from_attributes": True}


class PatientListItem(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    national_id: str | None
    age: int | None
    phone: str | None
    whatsapp: str | None

    model_config = {"from_attributes": True}
