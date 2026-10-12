import uuid

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TimestampMixin, UUIDPKMixin


class Clinic(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    tax_id: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(200))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str | None] = mapped_column(String(20), default="#0D7F76")
    secondary_color: Mapped[str | None] = mapped_column(String(20), default="#111827")
    timezone: Mapped[str] = mapped_column(String(50), default="America/Guayaquil")
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---- Personalización (asistente de configuración inicial) ----
    # independiente | consultorio | clinica: decide qué se muestra por defecto.
    practice_type: Mapped[str] = mapped_column(String(20), default="clinica", server_default="clinica")
    # El logo se guarda como data URL (PNG/JPEG/WebP, máx. ~400 KB): así sale
    # igual en la web, la app y los documentos impresos sin servir archivos.
    logo_data: Mapped[str | None] = mapped_column(Text)
    slogan: Mapped[str | None] = mapped_column(String(200))
    # Texto al pie de recibos, estados de cuenta y certificados.
    document_footer: Mapped[str | None] = mapped_column(String(400))
    # Horario de atención: lo usan los huecos libres de la agenda.
    opens_at: Mapped[str] = mapped_column(String(5), default="08:00", server_default="08:00")
    closes_at: Mapped[str] = mapped_column(String(5), default="19:00", server_default="19:00")
    # Días laborables: 1=lunes … 7=domingo.
    work_days: Mapped[str] = mapped_column(String(7), default="123456", server_default="123456")
    # Módulos que la consulta prefiere no ver en el menú (no quita permisos).
    hidden_modules: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    setup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ---- Legal y cumplimiento ----
    # Representante legal (firma contratos; en una persona natural es ella misma).
    legal_rep_name: Mapped[str | None] = mapped_column(String(200))
    legal_rep_id: Mapped[str | None] = mapped_column(String(20))
    # Delegado de protección de datos (LOPDP): a quién escriben los pacientes.
    dpo_name: Mapped[str | None] = mapped_column(String(200))
    dpo_email: Mapped[str | None] = mapped_column(String(200))
    # Permiso de funcionamiento del establecimiento de salud (ACESS) y su vigencia.
    health_permit_number: Mapped[str | None] = mapped_column(String(60))
    health_permit_expires_on: Mapped[date | None] = mapped_column(Date)
    # Datos tributarios (SRI) que salen en comprobantes.
    tax_regime: Mapped[str] = mapped_column(String(30), default="general", server_default="general")
    keeps_accounting: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    special_taxpayer: Mapped[str | None] = mapped_column(String(20))
    sri_establishment: Mapped[str] = mapped_column(String(3), default="001", server_default="001")
    sri_emission_point: Mapped[str] = mapped_column(String(3), default="001", server_default="001")
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, server_default="0")
    # Años que se conserva la historia clínica (se informa en el aviso de privacidad).
    record_retention_years: Mapped[int] = mapped_column(Integer, default=15, server_default="15")
    # Cláusulas propias que la consulta añade a su aviso de privacidad.
    privacy_extra: Mapped[str | None] = mapped_column(Text)
    # Cierre de sesión por inactividad, en minutos (web y celular).
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    # Aceptación de los Términos de uso y del contrato de encargo de tratamiento.
    terms_version: Mapped[str | None] = mapped_column(String(20))
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_accepted_by: Mapped[str | None] = mapped_column(String(200))

    branches: Mapped[list["Branch"]] = relationship(back_populates="clinic")


class Branch(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "branches"

    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)

    clinic: Mapped["Clinic"] = relationship(back_populates="branches")
    operatories: Mapped[list["Operatory"]] = relationship(back_populates="branch")


class Operatory(UUIDPKMixin, TimestampMixin, Base):
    """Consultorio / sillón dental."""

    __tablename__ = "operatories"

    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    branch: Mapped["Branch"] = relationship(back_populates="operatories")
