import uuid
from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    before: dict | None = None,
    after: dict | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            clinic_id=clinic_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            # before/after can carry dates, UUIDs, Decimals, etc. — normalize
            # to plain JSON-safe values so this never blows up on a type the
            # caller didn't think to stringify.
            before=jsonable_encoder(before) if before is not None else None,
            after=jsonable_encoder(after) if after is not None else None,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
    )
