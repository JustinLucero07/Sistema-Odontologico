import uuid

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.rate_limit import limiter
from app.modules.portal import service
from app.modules.portal.schemas import (
    PortalLinkCreated,
    PortalLinkOut,
    PortalView,
    RevokeRequest,
)

# Staff-facing: issuing and revoking links.
admin_router = APIRouter(prefix="/api/v1/patients/{patient_id}/portal", tags=["portal"])
manage_router = APIRouter(prefix="/api/v1/portal", tags=["portal"])
# Patient-facing and UNAUTHENTICATED: the token in the path is the credential.
public_router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@admin_router.get("", response_model=list[PortalLinkOut])
async def get_links(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    return await service.list_links(db, current_user.clinic_id, patient_id)


@admin_router.post("", response_model=PortalLinkCreated, status_code=201)
async def post_link(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:write")),
):
    access, raw = await service.create_link(
        db, current_user.clinic_id, current_user.id, patient_id
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
# The only unauthenticated endpoint that returns patient data, so it is the
# one worth guessing at. A token is 64 URL-safe characters, but a rate limit
# turns "computationally hopeless" into "visibly hopeless".
@limiter.limit("20/minute")
async def get_portal_view(
    request: Request,
    token: str = Path(min_length=20, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """No authentication dependency: the token IS the credential.

    It is looked up by hash, and an expired, revoked or unknown token all give
    the same 404 — distinguishing them would let a stranger probe for live
    links."""
    access = await service.resolve(db, token)
    view = await service.build_view(db, access)
    await db.commit()
    return view
