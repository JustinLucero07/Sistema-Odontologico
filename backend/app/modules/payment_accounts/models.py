from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class PaymentAccount(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "payment_accounts"

    label: Mapped[str] = mapped_column(String(80), nullable=False)  # Banco Pichincha, DeUna…
    qr_data: Mapped[str | None] = mapped_column(Text)
    holder_name: Mapped[str | None] = mapped_column(String(150))
    holder_id: Mapped[str | None] = mapped_column(String(20))
    account_type: Mapped[str | None] = mapped_column(String(30))  # ahorros | corriente | otra
    account_number: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
