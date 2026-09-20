from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class DayCount(BaseModel):
    date: str
    count: int


class DashboardSummary(BaseModel):
    total_patients: int
    new_patients_30d: int
    appointments_today: int
    appointments_this_week: int
    appointments_previous_week: int
    treatments_pending: int
    appointments_by_status: list[StatusCount]
    appointments_per_day: list[DayCount]
    budget_accepted_total: float
    budget_awaiting_total: float
