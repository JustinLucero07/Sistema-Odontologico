import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.imaging import service
from app.modules.imaging.models import IMAGE_TYPES, TOOTH_SCOPED_TYPES
from app.modules.imaging.schemas import ClinicalImageOut, ImageArchiveRequest

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/images", tags=["imaging"])
router = APIRouter(prefix="/api/v1/images", tags=["imaging"])


@router.get("/types")
async def get_image_types(
    current_user: CurrentUser = Depends(require_permission("imaging:read")),
):
    return [
        {"code": code, "label": label, "tooth_scoped": code in TOOTH_SCOPED_TYPES}
        for code, label in IMAGE_TYPES
    ]


@patient_router.get("", response_model=list[ClinicalImageOut])
async def get_images(
    patient_id: uuid.UUID,
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:read")),
):
    return await service.list_images(
        db, current_user.clinic_id, patient_id, include_archived=include_archived
    )


@patient_router.post("", response_model=ClinicalImageOut, status_code=201)
async def post_image(
    patient_id: uuid.UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    image_type: str = Form("otro"),
    description: str | None = Form(None),
    taken_on: date | None = Form(None),
    # Comma-separated FDI numbers, e.g. "16,17" for a bitewing.
    fdi_numbers: str | None = Form(None),
    professional_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:write")),
):
    content = await file.read()
    image = await service.upload_image(
        db,
        current_user.clinic_id,
        current_user.id,
        patient_id,
        title=title,
        image_type=image_type,
        description=description,
        taken_on=taken_on,
        fdi_numbers=fdi_numbers,
        professional_id=professional_id,
        filename=file.filename or "imagen",
        content=content,
        mime_type=file.content_type,
    )
    await db.commit()
    return image


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:read")),
):
    image, content = await service.read_image(
        db, current_user.clinic_id, current_user.id, image_id
    )
    await db.commit()
    return Response(
        content=content,
        media_type=image.mime_type or "application/octet-stream",
        # Inline, not an attachment: the viewer shows these in place. Clinical
        # images are never cached by a shared proxy.
        headers={
            "Content-Disposition": f'inline; filename="{image.original_filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.post("/{image_id}/archive", response_model=ClinicalImageOut)
async def post_archive_image(
    image_id: uuid.UUID,
    payload: ImageArchiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:write")),
):
    image = await service.archive_image(
        db, current_user.clinic_id, current_user.id, image_id, payload.reason
    )
    await db.commit()
    return image
