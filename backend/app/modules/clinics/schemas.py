import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from app.modules.privacy.constants import TERMS_VERSION


class ClinicOut(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str | None
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    logo_url: str | None
    primary_color: str | None
    secondary_color: str | None
    timezone: str
    currency: str
    practice_type: str
    logo_data: str | None
    slogan: str | None
    document_footer: str | None
    opens_at: str
    closes_at: str
    work_days: str
    hidden_modules: list[str]
    setup_completed_at: datetime | None
    legal_rep_name: str | None
    legal_rep_id: str | None
    dpo_name: str | None
    dpo_email: str | None
    health_permit_number: str | None
    health_permit_expires_on: date | None
    tax_regime: str
    keeps_accounting: bool
    special_taxpayer: str | None
    sri_establishment: str
    sri_emission_point: str
    vat_rate: Decimal
    record_retention_years: int
    privacy_extra: str | None
    session_timeout_minutes: int
    terms_version: str | None
    terms_accepted_at: datetime | None
    terms_accepted_by: str | None
    terms_current_version: str = TERMS_VERSION

    model_config = {"from_attributes": True}


PRACTICE_TYPES = {"independiente", "consultorio", "clinica"}
# Módulos que se pueden ocultar del menú. Ocultar no quita permisos: la
# función sigue existiendo y se puede volver a mostrar cuando se necesite.
OPTIONAL_MODULES = {"inventory", "laboratory", "credits", "reports", "cash", "opportunities", "messages", "consents"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_LOGO = 600_000  # ~400 KB de imagen en base64


class BrandingFields(BaseModel):
    """Lo que se elige en el asistente y en Configuración › Personalización."""

    practice_type: str | None = None
    logo_data: str | None = None
    slogan: str | None = Field(default=None, max_length=200)
    document_footer: str | None = Field(default=None, max_length=400)
    primary_color: str | None = None
    secondary_color: str | None = None
    opens_at: str | None = None
    closes_at: str | None = None
    work_days: str | None = None
    hidden_modules: list[str] | None = None

    @field_validator("practice_type")
    @classmethod
    def _tipo(cls, v):
        if v is not None and v not in PRACTICE_TYPES:
            raise ValueError("Tipo de consulta no válido")
        return v

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def _color(cls, v):
        if v is not None and not HEX.match(v):
            raise ValueError("Color no válido: use el formato #RRGGBB")
        return v

    @field_validator("opens_at", "closes_at")
    @classmethod
    def _hora(cls, v):
        if v is not None and not HORA.match(v):
            raise ValueError("Hora no válida: use HH:MM")
        return v

    @field_validator("work_days")
    @classmethod
    def _dias(cls, v):
        if v is None:
            return v
        dias = "".join(sorted(set(v)))
        if not dias or any(c not in "1234567" for c in dias):
            raise ValueError("Días laborables no válidos")
        return dias

    @field_validator("hidden_modules")
    @classmethod
    def _modulos(cls, v):
        if v is None:
            return v
        desconocidos = set(v) - OPTIONAL_MODULES
        if desconocidos:
            raise ValueError(f"Módulos desconocidos: {', '.join(sorted(desconocidos))}")
        return sorted(set(v))

    @field_validator("logo_data")
    @classmethod
    def _logo(cls, v):
        if v in (None, ""):
            return None
        if not re.match(r"^data:image/(png|jpeg|webp|svg\+xml);base64,", v):
            raise ValueError("El logo debe ser una imagen PNG, JPG, WebP o SVG")
        if len(v) > MAX_LOGO:
            raise ValueError("El logo es demasiado grande (máximo 400 KB)")
        return v


TAX_REGIME_CODES = {"general", "rimpe_emprendedor", "rimpe_negocio_popular"}
SRI_CODE = re.compile(r"^\d{3}$")


class LegalFields(BaseModel):
    """Configuración › Legal y cumplimiento."""

    legal_rep_name: str | None = Field(default=None, max_length=200)
    legal_rep_id: str | None = Field(default=None, max_length=20)
    dpo_name: str | None = Field(default=None, max_length=200)
    dpo_email: str | None = Field(default=None, max_length=200)
    health_permit_number: str | None = Field(default=None, max_length=60)
    health_permit_expires_on: date | None = None
    tax_regime: str | None = None
    keeps_accounting: bool | None = None
    special_taxpayer: str | None = Field(default=None, max_length=20)
    sri_establishment: str | None = None
    sri_emission_point: str | None = None
    vat_rate: Decimal | None = Field(default=None, ge=0, le=100)
    record_retention_years: int | None = Field(default=None, ge=1, le=100)
    privacy_extra: str | None = Field(default=None, max_length=4000)
    session_timeout_minutes: int | None = Field(default=None, ge=0, le=720)

    @field_validator("tax_regime")
    @classmethod
    def _regimen(cls, v):
        if v is not None and v not in TAX_REGIME_CODES:
            raise ValueError("Régimen tributario no válido")
        return v

    @field_validator("sri_establishment", "sri_emission_point")
    @classmethod
    def _sri(cls, v):
        if v is not None and not SRI_CODE.match(v):
            raise ValueError("Use tres dígitos, por ejemplo 001")
        return v

    @field_validator("dpo_email")
    @classmethod
    def _correo(cls, v):
        if v and "@" not in v:
            raise ValueError("Correo del delegado no válido")
        return v or None


class ClinicUpdate(BrandingFields, LegalFields):
    name: str | None = None
    legal_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    timezone: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        # Los reportes cuentan los días en esta zona: una mal escrita los
        # desplazaría sin avisar, así que se rechaza al guardarla.
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"Zona horaria desconocida: {value}")
        return value


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = None
    is_main: bool = False


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    is_main: bool | None = None


class BranchOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    is_main: bool

    model_config = {"from_attributes": True}


class OperatoryCreate(BaseModel):
    branch_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)


class OperatoryUpdate(BaseModel):
    branch_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class OperatoryOut(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class ClinicSetup(BrandingFields):
    """Asistente de bienvenida: todo de una vez, y marca la configuración como
    terminada. Si la consulta es de una sola persona, el administrador queda
    también como el profesional que atiende."""

    name: str = Field(min_length=2, max_length=200)
    legal_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    practice_type: str
    i_am_dentist: bool = False
    # Sin aceptar los Términos de uso y el contrato de encargo no se termina.
    accept_terms: bool = False
    license_number: str | None = Field(default=None, max_length=100)
    specialty: str | None = Field(default=None, max_length=120)


class Branding(BaseModel):
    """Lo que cualquier usuario necesita para pintar la interfaz."""

    name: str
    practice_type: str
    logo_data: str | None
    slogan: str | None
    primary_color: str | None
    secondary_color: str | None
    hidden_modules: list[str]
    setup_completed: bool
    opens_at: str
    closes_at: str
    work_days: str
    session_timeout_minutes: int = 30
    terms_pending: bool = False
    health_permit_expires_on: date | None = None
