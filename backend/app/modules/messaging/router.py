import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.messaging import service
from app.modules.messaging.models import MESSAGE_CHANNELS
from app.modules.messaging.schemas import (
    DispatchResult,
    MessageCreate,
    MessageOut,
    ProviderStatus,
    TemplateIn,
    TemplateOut,
)

router = APIRouter(prefix="/api/v1/messaging", tags=["messaging"])


@router.get("/status", response_model=ProviderStatus)
async def get_status(
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return service.provider_status()


@router.get("/channels")
async def get_channels(
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return [{"code": code, "label": label} for code, label in MESSAGE_CHANNELS]


@router.get("/templates", response_model=list[TemplateOut])
async def get_templates(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    templates = await service.list_templates(db, current_user.clinic_id)
    await db.commit()
    return templates


@router.put("/templates", response_model=TemplateOut)
async def put_template(
    payload: TemplateIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    template = await service.upsert_template(
        db, current_user.clinic_id, current_user.id, payload
    )
    await db.commit()
    return template


@router.get("/messages", response_model=list[MessageOut])
async def get_messages(
    patient_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:read")),
):
    return await service.list_messages(
        db, current_user.clinic_id, patient_id=patient_id, limit=limit
    )


@router.post("/messages", response_model=MessageOut, status_code=201)
async def post_message(
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:write")),
):
    message = await service.send_message(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return message


@router.post("/dispatch", response_model=DispatchResult)
async def post_dispatch(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("appointments:write")),
):
    """Sends the reminders whose moment has arrived.

    Exposed as an endpoint rather than hidden in a background loop so a real
    deployment can drive it from cron and see exactly what happened."""
    result = await service.dispatch_due_reminders(
        db, current_user.clinic_id, current_user.id
    )
    await db.commit()
    return result
