import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.appointments.constants import APPOINTMENT_STATUS_CODES, REMINDER_CHANNEL_CODES


class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    operatory_id: uuid.UUID | None = None
    treatment_id: uuid.UUID | None = None
    treatment_plan_item_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime
    status: str = "programada"
    color_hex: str | None = None
    notes: str | None = None
    reminder_channels: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in APPOINTMENT_STATUS_CODES:
            raise ValueError(f"Estado inválido: {value}")
        return value

    @field_validator("reminder_channels")
    @classmethod
    def validate_channels(cls, value: list[str]) -> list[str]:
        for channel in value:
            if channel not in REMINDER_CHANNEL_CODES:
                raise ValueError(f"Canal de recordatorio inválido: {channel}")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "AppointmentCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("La hora de fin debe ser posterior a la de inicio")
        return self


class AppointmentUpdate(BaseModel):
    professional_id: uuid.UUID | None = None
    operatory_id: uuid.UUID | None = None
    treatment_id: uuid.UUID | None = None
    treatment_plan_item_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    color_hex: str | None = None
    notes: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str
    cancellation_reason: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in APPOINTMENT_STATUS_CODES:
            raise ValueError(f"Estado inválido: {value}")
        return value


class AppointmentReminderOut(BaseModel):
    id: uuid.UUID
    channel: str
    offset_minutes: int
    scheduled_for: datetime
    status: str
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class AppointmentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    professional_id: uuid.UUID
    professional_name: str
    operatory_id: uuid.UUID | None
    treatment_id: uuid.UUID | None
    treatment_name: str | None
    treatment_plan_item_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    status: str
    color_hex: str | None
    notes: str | None
    cancellation_reason: str | None
    reminders: list[AppointmentReminderOut]

    model_config = {"from_attributes": True}

    @classmethod
    def from_appointment(cls, appointment, patient, professional, treatment) -> "AppointmentOut":
        return cls(
            id=appointment.id,
            patient_id=appointment.patient_id,
            patient_name=f"{patient.first_name} {patient.last_name}",
            professional_id=appointment.professional_id,
            professional_name=f"{professional.first_name} {professional.last_name}",
            operatory_id=appointment.operatory_id,
            treatment_id=appointment.treatment_id,
            treatment_name=treatment.name if treatment else None,
            treatment_plan_item_id=appointment.treatment_plan_item_id,
            starts_at=appointment.starts_at,
            ends_at=appointment.ends_at,
            duration_minutes=appointment.duration_minutes,
            status=appointment.status,
            color_hex=appointment.color_hex or professional.color_hex,
            notes=appointment.notes,
            cancellation_reason=appointment.cancellation_reason,
            reminders=[AppointmentReminderOut.model_validate(r) for r in appointment.reminders],
        )
