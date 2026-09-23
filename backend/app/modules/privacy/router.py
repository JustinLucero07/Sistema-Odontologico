import json
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.modules.clinics.models import Clinic
from app.modules.privacy import service
from app.modules.privacy.constants import CONFIDENTIALITY_VERSION, PRIVACY_POLICY_VERSION
from app.modules.privacy.schemas import AccessEntry, ConsentCreate, ConsentOut, LegalController, PrivacyStatus

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/privacy", tags=["privacy"])
legal_router = APIRouter(prefix="/api/v1/legal", tags=["privacy"])


@patient_router.get("", response_model=PrivacyStatus)
async def get_privacy(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    return await service.privacy_status(db, current_user.clinic_id, patient_id)


@patient_router.post("/consents", response_model=ConsentOut, status_code=201)
async def post_consent(
    patient_id: uuid.UUID,
    payload: ConsentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:write")),
):
    consent = await service.record_consent(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return consent


@patient_router.get("/access-log", response_model=list[AccessEntry])
async def get_access_log(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    return await service.access_log(db, current_user.clinic_id, patient_id)


@patient_router.get("/export")
async def get_export(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:export")),
):
    data = await service.export_patient_data(db, current_user.clinic_id, current_user.id, patient_id)
    await db.commit()
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="datos-paciente-{patient_id}.json"'},
    )


@legal_router.get("/controller", response_model=LegalController)
async def get_controller(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    clinic = await db.get(Clinic, current_user.clinic_id)
    return LegalController(
        name=clinic.name,
        legal_name=clinic.legal_name,
        tax_id=clinic.tax_id,
        address=clinic.address,
        phone=clinic.phone,
        email=clinic.email,
        privacy_policy_version=PRIVACY_POLICY_VERSION,
        confidentiality_version=CONFIDENTIALITY_VERSION,
    )
