import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PortalLinkOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    expires_at: datetime
    created_at: datetime
    last_used_at: datetime | None
    use_count: int
    revoked_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class PortalLinkCreated(PortalLinkOut):
    """The raw token is returned exactly ONCE, at creation.

    Only its hash is stored, so it cannot be shown again — the clinic sends the
    link now or issues a new one."""

    url: str


class PortalAppointment(BaseModel):
    starts_at: datetime
    professional_name: str | None
    treatment_name: str | None
    status: str


class PortalCharge(BaseModel):
    description: str
    issued_on: date
    amount: Decimal
    pending: Decimal


class PortalView(BaseModel):
    """What a patient sees. Read-only, and deliberately narrow: no clinical
    notes, no diagnoses, no documents. A link that lands in the wrong inbox
    must not expose a medical history."""

    patient_name: str
    clinic_name: str
    upcoming: list[PortalAppointment]
    past: list[PortalAppointment]
    balance: Decimal
    charges: list[PortalCharge]
    expires_at: datetime


class RevokeRequest(BaseModel):
    reason: str | None = None
