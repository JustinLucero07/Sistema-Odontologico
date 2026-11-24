from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DateRange(BaseModel):
    date_from: date
    date_to: date


class NamedAmount(BaseModel):
    key: str
    label: str
    amount: Decimal
    count: int


class AgingBucket(BaseModel):
    label: str
    amount: Decimal
    count: int


class FinancialReport(BaseModel):
    range: DateRange
    collected: Decimal
    charged: Decimal
    payment_count: int
    by_method: list[NamedAmount]
    by_professional: list[NamedAmount]
    daily: list[dict]
    outstanding_total: Decimal
    aging: list[AgingBucket]
    voided_total: Decimal
    voided_count: int


class BudgetConversion(BaseModel):
    accepted_count: int
    accepted_amount: Decimal
    rejected_count: int
    rejected_amount: Decimal
    pending_count: int
    pending_amount: Decimal
    conversion_rate: float | None


class ClinicalReport(BaseModel):
    range: DateRange
    treatments_completed: int
    by_treatment: list[NamedAmount]
    by_professional: list[NamedAmount]
    top_diagnoses: list[NamedAmount]
    budgets: BudgetConversion


class AppointmentReport(BaseModel):
    range: DateRange
    total: int
    by_status: list[NamedAmount]
    by_professional: list[NamedAmount]
    by_weekday: list[NamedAmount]
    concluded: int
    attended: int
    no_show: int
    cancelled: int
    no_show_rate: float | None
    cancellation_rate: float | None


class PatientReport(BaseModel):
    range: DateRange
    new_patients: int
    total_active: int
    by_month: list[NamedAmount]
    by_sex: list[NamedAmount]
    by_age_band: list[NamedAmount]
    # Seen at least once in the last year, and the rest.
    seen_last_12m: int
    dormant: int


class ReportSummary(BaseModel):
    """What the reports landing page shows before anyone picks a report."""

    range: DateRange
    collected: Decimal
    outstanding: Decimal
    appointments: int
    no_show_rate: float | None
    new_patients: int
    treatments_completed: int
