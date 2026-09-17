import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantMixin:
    """Every clinic-scoped table carries clinic_id. Filtering by it is mandatory
    in every repository query — see TenantContext in app.core.deps."""

    @declared_attr
    def clinic_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
