from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class MailSettings(UUIDPKMixin, TenantMixin, Base):
    """Correo saliente de una consulta: facturas, recordatorios de citas y
    consentimientos para firmar. Cada consulta usa su propio buzón (Gmail,
    Outlook, el de su dominio…), así los pacientes reciben los correos de su
    consultorio y no de un remitente desconocido.

    La contraseña se guarda CIFRADA, igual que la firma electrónica."""

    __tablename__ = "mail_settings"
    __table_args__ = (UniqueConstraint("clinic_id", name="uq_mail_settings_clinic"),)

    host: Mapped[str | None] = mapped_column(String(200))
    port: Mapped[int] = mapped_column(Integer, default=587, server_default="587")
    # starttls (587) | ssl (465) | none (solo servidores internos)
    security: Mapped[str] = mapped_column(String(10), default="starttls", server_default="starttls")
    username: Mapped[str | None] = mapped_column(String(200))
    password: Mapped[bytes | None] = mapped_column(LargeBinary)
    from_email: Mapped[str | None] = mapped_column(String(200))
    from_name: Mapped[str | None] = mapped_column(String(200))
    # Recordatorios de citas por correo además de WhatsApp.
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_error: Mapped[str | None] = mapped_column(String(500))
