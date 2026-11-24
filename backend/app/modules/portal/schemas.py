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
    include_clinical: bool = False

    model_config = {"from_attributes": True}


class PortalLinkCreated(PortalLinkOut):
    url: str


class PortalAppointment(BaseModel):
    starts_at: datetime
    professional_name: str | None
    treatment_name: str | None
    status: str


class PortalCharge(BaseModel):
    id: uuid.UUID | None = None
    description: str
    issued_on: date
    amount: Decimal
    pending: Decimal


class PortalPaymentAccount(BaseModel):
    label: str
    qr_data: str | None = None
    holder_name: str | None = None
    holder_id: str | None = None
    account_type: str | None = None
    account_number: str | None = None
    email: str | None = None
    note: str | None = None

    model_config = {"from_attributes": True}


class PortalCuota(BaseModel):
    id: uuid.UUID
    number: int
    planned_on: date | None
    attended_on: date | None
    amount: Decimal
    paid: Decimal
    balance: Decimal
    status: str


class PortalOrtho(BaseModel):
    code: str
    appliance: str | None
    started_on: date | None
    estimated_months: int | None
    status: str
    controls_attended: int
    controls_total: int
    progress: float | None
    next_control_on: date | None
    next_control_overdue: bool
    agreed_total: Decimal
    paid: Decimal
    balance: Decimal
    cuotas: list[PortalCuota]


class PortalPlanItem(BaseModel):
    treatment: str
    fdi_number: str | None
    status: str
    status_label: str


class PortalHallazgo(BaseModel):
    fdi_number: str
    surface: str
    condition: str


class PortalComparacion(BaseModel):
    id: uuid.UUID
    title: str
    treatment: str | None
    before_id: uuid.UUID
    after_id: uuid.UUID


class PortalComprobante(BaseModel):
    id: uuid.UUID
    amount: Decimal
    paid_on: date
    destino: str
    status: str
    status_label: str
    reject_reason: str | None
    created_at: datetime


class PortalView(BaseModel):
    patient_name: str
    clinic_name: str
    upcoming: list[PortalAppointment]
    past: list[PortalAppointment]
    balance: Decimal
    charges: list[PortalCharge]
    expires_at: datetime
    payment_accounts: list[PortalPaymentAccount] = []
    ortodoncia: PortalOrtho | None = None
    plan: list[PortalPlanItem] = []
    odontograma: list[PortalHallazgo] = []
    comparaciones: list[PortalComparacion] = []
    comprobantes: list[PortalComprobante] = []
    incluye_clinica: bool = False


class LinkCreate(BaseModel):
    include_clinical: bool = False


class RevokeRequest(BaseModel):
    reason: str | None = None
