import uuid

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.rate_limit import limiter
from app.modules.clinics.models import Clinic
from app.modules.consents import pdf, service
from app.modules.patients.service import get_patient_or_404
from app.modules.professionals.models import Professional
from app.shared.archivos import cabeceras_archivo
from app.shared.voiding import VoidRequest
from app.modules.consents.schemas import (
    ConsentCreate,
    ConsentOut,
    ConsentSign,
    ConsentTemplateCreate,
    ConsentTemplateOut,
    ConsentTemplateUpdate,
    LibraryAdd,
    PublicConsentView,
    PublicSign,
    SignLinkOut,
    SignLinkRequest,
)

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/consents", tags=["consents"])
router = APIRouter(prefix="/api/v1/consents", tags=["consents"])
# Sin sesión: el enlace ES la credencial (como el portal del paciente).
public_router = APIRouter(prefix="/api/v1/public/consents", tags=["consents"])


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


@router.post("/{consent_id}/void", response_model=ConsentOut)
async def void_consent(
    consent_id: uuid.UUID,
    payload: VoidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    consent = await service.void_consent(db, current_user.clinic_id, current_user.id, consent_id, payload.reason)
    await db.commit()
    return consent


# ---------------------------------------------------------------- Biblioteca


@router.get("/library")
async def get_library(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    return await service.library(db, current_user.clinic_id)


@router.post("/library")
async def post_library(
    payload: LibraryAdd,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    n = await service.add_from_library(db, current_user.clinic_id, current_user.id, payload.names)
    await db.commit()
    return {"added": n}


# ---------------------------------------------------------------- Enlace y PDF


@router.post("/{consent_id}/sign-link", response_model=SignLinkOut)
async def post_sign_link(
    consent_id: uuid.UUID,
    payload: SignLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:write")),
):
    out = await service.create_sign_link(db, current_user.clinic_id, current_user.id, consent_id, payload.send_email)
    await db.commit()
    return out


@router.get("/{consent_id}/pdf")
async def get_pdf(
    consent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("consents:read")),
):
    consent = await service.get_consent_or_404(db, current_user.clinic_id, consent_id)
    paciente = await get_patient_or_404(db, current_user.clinic_id, consent.patient_id)
    clinica = (await db.execute(select(Clinic).where(Clinic.id == current_user.clinic_id))).scalar_one()
    profesional = None
    if consent.professional_id:
        profesional = (await db.execute(select(Professional).where(Professional.id == consent.professional_id))).scalar_one_or_none()
    nombre = f"consentimiento-{paciente.last_name}-{consent.created_at:%Y%m%d}.pdf".replace(" ", "-")
    return Response(
        pdf.generar(consent, paciente, clinica, profesional), media_type="application/pdf",
        headers=cabeceras_archivo(nombre, en_linea=True),
    )


# ---------------------------------------------------------------- Firma a distancia


@public_router.get("/{token}", response_model=PublicConsentView)
@limiter.limit("30/minute")
async def get_public(request: Request, token: str = Path(min_length=20, max_length=200), db: AsyncSession = Depends(get_db)):
    consent, paciente, clinica = await service.resolve_public(db, token)
    return PublicConsentView(
        clinic_name=clinica.name, clinic_logo=clinica.logo_data, clinic_color=clinica.primary_color,
        patient_name=f"{paciente.first_name} {paciente.last_name}", title=consent.title, body=consent.body,
        expires_at=consent.sign_token_expires_at,
    )


@public_router.post("/{token}/sign")
@limiter.limit("10/minute")
async def post_public_sign(
    request: Request,
    payload: PublicSign,
    token: str = Path(min_length=20, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else None)
    await service.sign_public(db, token, payload, ip, request.headers.get("user-agent"))
    await db.commit()
    return {"ok": True}
