import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.documents import service
from app.modules.documents.models import DOCUMENT_TYPES
from app.modules.documents.schemas import DocumentArchiveRequest, DocumentOut, DocumentUpdate

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/documents", tags=["documents"])
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("/types")
async def get_document_types(
    current_user: CurrentUser = Depends(require_permission("documents:read")),
):
    return [{"code": code, "label": label} for code, label in DOCUMENT_TYPES]


@patient_router.get("", response_model=list[DocumentOut])
async def get_documents(
    patient_id: uuid.UUID,
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:read")),
):
    return await service.list_documents(db, current_user.clinic_id, patient_id, include_archived)


@patient_router.post("", response_model=DocumentOut, status_code=201)
async def post_document(
    patient_id: uuid.UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("otro"),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:write")),
):
    content = await file.read()
    document = await service.upload_document(
        db,
        current_user.clinic_id,
        current_user.id,
        patient_id,
        title=title,
        document_type=document_type,
        description=description,
        filename=file.filename or "documento",
        content=content,
        mime_type=file.content_type,
    )
    await db.commit()
    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:read")),
):
    document, content = await service.read_document(
        db, current_user.clinic_id, current_user.id, document_id
    )
    await db.commit()
    return Response(
        content=content,
        media_type=document.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )


@router.put("/{document_id}", response_model=DocumentOut)
async def put_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:write")),
):
    document = await service.update_document(db, current_user.clinic_id, current_user.id, document_id, payload)
    await db.commit()
    return document


@router.post("/{document_id}/archive", response_model=DocumentOut)
async def post_archive_document(
    document_id: uuid.UUID,
    payload: DocumentArchiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:write")),
):
    document = await service.archive_document(
        db, current_user.clinic_id, current_user.id, document_id, payload.reason
    )
    await db.commit()
    return document


@router.post("/{document_id}/restore", response_model=DocumentOut)
async def post_restore_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:write")),
):
    document = await service.restore_document(db, current_user.clinic_id, current_user.id, document_id)
    await db.commit()
    return document
