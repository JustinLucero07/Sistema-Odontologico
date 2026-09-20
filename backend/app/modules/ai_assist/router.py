import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.ai_assist import service
from app.modules.ai_assist.models import SUGGESTION_KINDS
from app.modules.ai_assist.schemas import (
    AiStatus,
    DiscardRequest,
    SuggestionOut,
    SuggestionRequest,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/ai", tags=["ai"])


@router.get("/status", response_model=AiStatus)
async def get_status(
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    return service.ai_status()


@router.get("/kinds")
async def get_kinds(
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    return [{"code": code, "label": label} for code, label in SUGGESTION_KINDS]


@patient_router.get("/context")
async def get_context(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:read")),
):
    """Exactly what the assistant would be given. Exposed so a clinician can
    see the assistant's whole world before trusting a word of its output."""
    return {"context": await service.build_context(db, current_user.clinic_id, patient_id)}


@patient_router.get("/suggestions", response_model=list[SuggestionOut])
async def get_suggestions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:read")),
):
    return await service.list_suggestions(db, current_user.clinic_id, patient_id)


@patient_router.post("/suggestions", response_model=SuggestionOut, status_code=201)
async def post_suggestion(
    patient_id: uuid.UUID,
    payload: SuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:write")),
):
    suggestion = await service.create_suggestion(
        db, current_user.clinic_id, current_user.id, patient_id, payload
    )
    await db.commit()
    return suggestion


@router.post("/suggestions/{suggestion_id}/accept", response_model=SuggestionOut)
async def post_accept(
    suggestion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:write")),
):
    suggestion = await service.decide(
        db, current_user.clinic_id, current_user.id, suggestion_id, accept=True
    )
    await db.commit()
    return suggestion


@router.post("/suggestions/{suggestion_id}/discard", response_model=SuggestionOut)
async def post_discard(
    suggestion_id: uuid.UUID,
    payload: DiscardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("medical_history:write")),
):
    suggestion = await service.decide(
        db, current_user.clinic_id, current_user.id, suggestion_id,
        accept=False, reason=payload.reason,
    )
    await db.commit()
    return suggestion
