import uuid
from datetime import datetime, timezone

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
            before=before,
            after=after,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
    )
