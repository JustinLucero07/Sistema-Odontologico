import uuid

from sqlalchemy import Boolean, ForeignKey, String
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
    primary_color: Mapped[str | None] = mapped_column(String(20), default="#0F6FFF")
    secondary_color: Mapped[str | None] = mapped_column(String(20), default="#111827")
    timezone: Mapped[str] = mapped_column(String(50), default="America/Guayaquil")
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
