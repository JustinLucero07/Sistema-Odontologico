import uuid
from datetime import datetime

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class DayCount(BaseModel):
    date: str
    count: int


class AgendaEntry(BaseModel):
    id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    patient_id: uuid.UUID
    patient_name: str
    professional_name: str
    professional_color: str | None
    treatment_name: str | None


class BirthdayEntry(BaseModel):
    patient_id: uuid.UUID
    name: str
    turns: int
    whatsapp: str | None


class Attention(BaseModel):
    """Lo que alguien tiene que resolver hoy. Cada cifra es None cuando el
    usuario no tiene permiso para ver ese módulo, no cero: cero significaría
    "todo en orden", y eso no lo sabe."""

    stock_alerts: int | None
    lab_overdue: int | None
    budgets_awaiting: int | None
    birthdays: list[BirthdayEntry] | None


class DashboardSummary(BaseModel):
    today: str
    total_patients: int
    new_patients_30d: int
    appointments_today: int
    appointments_this_week: int
    appointments_previous_week: int
    treatments_pending: int
    appointments_by_status: list[StatusCount]
    appointments_per_day: list[DayCount]
    today_agenda: list[AgendaEntry] | None
    # Dinero: solo para quien puede ver caja o presupuestos; si no, None.
    budget_accepted_total: float | None
    budget_awaiting_total: float | None
    income_month: str | None
    income_previous_month_same_period: str | None
    receivables_total: str | None
    attention: Attention
