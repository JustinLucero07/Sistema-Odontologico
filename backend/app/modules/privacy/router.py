import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.modules.clinics.models import Clinic
from app.modules.privacy import service
from app.modules.privacy.constants import (
    CONFIDENTIALITY_VERSION,
    PRIVACY_POLICY_VERSION,
    RIGHTS_KINDS,
    RIGHTS_STATUSES,
    TAX_REGIMES,
    TERMS_VERSION,
)
from app.modules.privacy.documents import DOCUMENTS
from app.modules.privacy.schemas import (
    AccessEntry,
    ConsentCreate,
    ConsentOut,
    LegalController,
    LegalDocument,
    PrivacyStatus,
    RightsRequestIn,
    RightsRequestOut,
)

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
        legal_rep_name=clinic.legal_rep_name,
        dpo_name=clinic.dpo_name,
        dpo_email=clinic.dpo_email,
        health_permit_number=clinic.health_permit_number,
        record_retention_years=clinic.record_retention_years,
        privacy_extra=clinic.privacy_extra,
        terms_version=TERMS_VERSION,
        logo_data=clinic.logo_data,
        primary_color=clinic.primary_color,
        slogan=clinic.slogan,
        document_footer=clinic.document_footer,
    )


@legal_router.get("/catalogs")
async def get_catalogs(current_user: CurrentUser = Depends(get_current_user)):
    """Listas para los formularios de Legal y cumplimiento."""
    def opciones(d: dict[str, str]) -> list[dict]:
        return [{"code": k, "label": v} for k, v in d.items()]

    return {
        "rights_kinds": opciones(RIGHTS_KINDS),
        "rights_statuses": opciones(RIGHTS_STATUSES),
        "tax_regimes": opciones(TAX_REGIMES),
    }


@legal_router.get("/documents/{code}", response_model=LegalDocument)
async def get_document(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if code not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    titulo, generar = DOCUMENTS[code]
    clinic = await db.get(Clinic, current_user.clinic_id)
    return LegalDocument(code=code, title=titulo, version=TERMS_VERSION, sections=generar(clinic))


@legal_router.get("/requests", response_model=list[RightsRequestOut])
async def get_requests(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    return await service.list_rights_requests(db, current_user.clinic_id)


@legal_router.post("/requests", response_model=RightsRequestOut, status_code=201)
async def post_request(
    payload: RightsRequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.save_rights_request(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return out


@legal_router.put("/requests/{request_id}", response_model=RightsRequestOut)
async def put_request(
    request_id: uuid.UUID,
    payload: RightsRequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.save_rights_request(db, current_user.clinic_id, current_user.id, payload, request_id)
    await db.commit()
    return out


@legal_router.delete("/requests/{request_id}", status_code=204)
async def delete_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    await service.delete_rights_request(db, current_user.clinic_id, current_user.id, request_id)
    await db.commit()
    return Response(status_code=204)
