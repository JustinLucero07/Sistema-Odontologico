from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class MailSettingsOut(BaseModel):
    configured: bool
    source: str  # consulta | servidor | ninguno
    host: str | None
    port: int
    security: str
    username: str | None
    has_password: bool
    from_email: str | None
    from_name: str | None
    reminders_enabled: bool
    last_test_at: datetime | None
    last_test_ok: bool | None
    last_error: str | None


class MailSettingsUpdate(BaseModel):
    host: str | None = Field(default=None, max_length=200)
    port: int | None = Field(default=None, ge=1, le=65535)
    security: str | None = None
    username: str | None = Field(default=None, max_length=200)
    # Vacío o ausente = conservar la guardada.
    password: str | None = Field(default=None, max_length=300)
    from_email: EmailStr | None = None
    from_name: str | None = Field(default=None, max_length=200)
    reminders_enabled: bool | None = None

    @field_validator("security")
    @classmethod
    def seguridad(cls, v: str | None) -> str | None:
        if v is not None and v not in ("starttls", "ssl", "none"):
            raise ValueError("Seguridad inválida (starttls, ssl o none)")
        return v


class MailTest(BaseModel):
    to: EmailStr
