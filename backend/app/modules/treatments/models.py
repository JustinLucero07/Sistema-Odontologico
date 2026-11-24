from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Treatment(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "treatments"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    default_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    vat_code: Mapped[str] = mapped_column(String(2), default="0", server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
