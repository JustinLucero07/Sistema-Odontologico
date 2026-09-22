"""Anular en vez de borrar, para los registros clínicos.

Un diagnóstico o una receta mal hechos no desaparecen: quedan en la historia
marcados como anulados, con quién, cuándo y por qué. Así la ficha sigue
contando lo que realmente pasó, que es lo que exige un expediente clínico.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class VoidableMixin:
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)

    @declared_attr
    def voided_by_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class VoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def apply_void(record: VoidableMixin, actor_id: uuid.UUID, reason: str, label: str) -> None:
    if record.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{label} ya está anulado")
    record.voided_at = datetime.now(timezone.utc)
    record.voided_by_id = actor_id
    record.void_reason = reason.strip()
