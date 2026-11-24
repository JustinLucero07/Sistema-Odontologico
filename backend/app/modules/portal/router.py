import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Path, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.rate_limit import limiter
from app.shared.archivos import cabeceras_archivo
from app.modules.portal import comprobantes, service
from app.modules.portal.schemas import (
    PortalLinkCreated,
    LinkCreate,
    PortalComprobante,
    PortalLinkOut,
    PortalView,
    RevokeRequest,
)

# Staff-facing: issuing and revoking links.
from app.modules.patients.service import get_patient_or_404

admin_router = APIRouter(prefix="/api/v1/patients/{patient_id}/portal", tags=["portal"])
manage_router = APIRouter(prefix="/api/v1/portal", tags=["portal"])
public_router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@admin_router.get("", response_model=list[PortalLinkOut])
async def get_links(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    await get_patient_or_404(db, current_user.clinic_id, patient_id)
    return await service.list_links(db, current_user.clinic_id, patient_id)


@admin_router.post("", response_model=PortalLinkCreated, status_code=201)
async def post_link(
    patient_id: uuid.UUID,
    payload: LinkCreate | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:write")),
):
    access, raw = await service.create_link(
        db, current_user.clinic_id, current_user.id, patient_id,
        include_clinical=bool(payload and payload.include_clinical),
    )
    await db.commit()
    settings = get_settings()
    return PortalLinkCreated(
        id=access.id,
        patient_id=access.patient_id,
        expires_at=access.expires_at,
        created_at=access.created_at,
        last_used_at=access.last_used_at,
        use_count=access.use_count,
        revoked_at=access.revoked_at,
        is_active=access.is_active,
        include_clinical=access.include_clinical,
        # Shown once. Only the hash is stored, so there is no second chance.
        url=f"{settings.PORTAL_BASE_URL}/portal/{raw}",
    )


@manage_router.post("/{access_id}/revoke", response_model=PortalLinkOut)
async def post_revoke(
    access_id: uuid.UUID,
    payload: RevokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:write")),
):
    access = await service.revoke(
        db, current_user.clinic_id, current_user.id, access_id, payload.reason
    )
    await db.commit()
    return access


@public_router.get("/view/{token}", response_model=PortalView)
@limiter.limit("20/minute")
async def get_portal_view(
    request: Request,
    token: str = Path(min_length=20, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    access = await service.resolve(db, token)
    view = await service.build_view(db, access)
    await db.commit()
    return view


@public_router.get("/view/{token}/images/{image_id}")
@limiter.limit("60/minute")
async def get_portal_image(
    request: Request,
    image_id: uuid.UUID,
    token: str = Path(min_length=20, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    access = await service.resolve(db, token)
    imagen, contenido = await service.imagen_del_portal(db, access, image_id)
    return Response(
        content=contenido,
        media_type=imagen.mime_type or "image/jpeg",
        headers={**cabeceras_archivo(imagen.original_filename, en_linea=True), "Cache-Control": "private, max-age=600"},
    )


@public_router.post("/view/{token}/receipts", response_model=PortalComprobante, status_code=201)
@limiter.limit("6/minute")
async def post_portal_receipt(
    request: Request,
    tareas: BackgroundTasks,
    token: str = Path(min_length=20, max_length=200),
    file: UploadFile = File(...),
    amount: Decimal = Form(...),
    paid_on: date | None = Form(default=None),
    reference: str | None = Form(default=None, max_length=120),
    note: str | None = Form(default=None, max_length=1000),
    charge_id: uuid.UUID | None = Form(default=None),
    ortho_control_id: uuid.UUID | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    access = await service.resolve(db, token)
    contenido = await file.read(comprobantes.MAX_BYTES + 1)
    r = await comprobantes.crear_desde_portal(
        db, access, amount=amount, paid_on=paid_on, reference=reference, note=note,
        charge_id=charge_id, ortho_control_id=ortho_control_id,
        filename=file.filename or "comprobante", content=contenido,
    )
    salida = (await comprobantes.a_salida(db, [r]))[0]
    await db.commit()
    tareas.add_task(comprobantes.avisar_clinica, r.id, request.app.dependency_overrides.get(get_db, get_db))
    return PortalComprobante(**salida.model_dump(include={"id", "amount", "paid_on", "destino", "status", "status_label", "reject_reason", "created_at"}))
