import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Specialty(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "specialties"

    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Professional(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "professionals"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialty_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("specialties.id"), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100))
    color_hex: Mapped[str] = mapped_column(String(20), default="#0F6FFF")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    specialty: Mapped["Specialty"] = relationship()
