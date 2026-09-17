from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Patient(UUIDPKMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(50), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(20))  # M | F | O
    phone: Mapped[str | None] = mapped_column(String(50))
    whatsapp: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(120))
    occupation: Mapped[str | None] = mapped_column(String(150))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def age(self) -> int | None:
        if self.birth_date is None:
            return None
        today = date.today()
        years = today.year - self.birth_date.year
        had_birthday = (today.month, today.day) >= (self.birth_date.month, self.birth_date.day)
        return years if had_birthday else years - 1
