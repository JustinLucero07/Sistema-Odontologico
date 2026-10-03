import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PatientContact(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    phone: str | None
    whatsapp: str | None
    # False si el paciente retiró su autorización de comunicaciones: la
    # oportunidad se muestra, pero sin botón de WhatsApp.
    contact_allowed: bool


class RecallItem(PatientContact):
    last_visit: date
    months_since: int


class PendingTreatmentItem(PatientContact):
    treatments: list[str]
    amount: Decimal


class DebtorItem(PatientContact):
    pending: Decimal
    oldest_charge_on: date


class BirthdayItem(PatientContact):
    birth_date: date
    turns: int
    days_until: int


class UnconfirmedItem(PatientContact):
    appointment_id: uuid.UUID
    starts_at: datetime
    professional_name: str


class Opportunities(BaseModel):
    clinic_name: str
    recall: list[RecallItem]
    pending_treatments: list[PendingTreatmentItem]
    debtors: list[DebtorItem]
    birthdays: list[BirthdayItem]
    unconfirmed: list[UnconfirmedItem]


class FreeSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
