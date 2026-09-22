import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.consents import service
from app.modules.consents.schemas import (
    ConsentCreate,
    ConsentOut,
    ConsentSign,
    ConsentTemplateCreate,
    ConsentTemplateOut,
    ConsentTemplateUpdate,
)

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/consents", tags=["consents"])
router = APIRouter(prefix="/api/v1/consents", tags=["consents"])


@router.get("/templates", response_model=list[ConsentTemplateOut])
async def get_templates(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:read")),
):
    return await service.list_templates(db, current_user.clinic_id, include_inactive)


@router.put("/templates/{template_id}", response_model=ConsentTemplateOut)
async def put_template(
    template_id: uuid.UUID,
    payload: ConsentTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    template = await service.update_template(db, current_user.clinic_id, current_user.id, template_id, payload)
    await db.commit()
    return template


@router.post("/templates", response_model=ConsentTemplateOut, status_code=201)
async def post_template(
    payload: ConsentTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    template = await service.create_template(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return template


@router.put("/{consent_id}/sign", response_model=ConsentOut)
async def sign_consent(
    consent_id: uuid.UUID,
    payload: ConsentSign,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    consent = await service.sign_consent(db, current_user.clinic_id, current_user.id, consent_id, payload)
    await db.commit()
    return consent


@patient_router.get("", response_model=list[ConsentOut])
async def get_consents(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:read")),
):
    return await service.list_consents(db, current_user.clinic_id, patient_id)


@patient_router.post("", response_model=ConsentOut, status_code=201)
async def post_consent(
    patient_id: uuid.UUID,
    payload: ConsentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    consent = await service.create_consent(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return consent
