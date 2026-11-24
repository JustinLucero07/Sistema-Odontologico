import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.audit import record_audit
from app.core.database import Base, get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.imaging.models import ClinicalImage
from app.modules.patients.service import get_patient_or_404
from app.shared.mixins import TenantMixin, UUIDPKMixin


class ImageComparison(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "image_comparisons"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    before_image_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_images.id"), nullable=False)
    after_image_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_images.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    treatment: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    # Autorización del paciente para usar las fotos fuera de la historia.
    share_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    share_consent_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


def _texto(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


class ComparisonFields(BaseModel):
    treatment: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)
    share_consent: bool | None = None

    @field_validator("treatment", "notes")
    @classmethod
    def _limpiar(cls, v):
        return _texto(v)


class ComparisonCreate(ComparisonFields):
    before_image_id: uuid.UUID
    after_image_id: uuid.UUID
    title: str = Field(min_length=1, max_length=120)


class ComparisonUpdate(ComparisonFields):
    before_image_id: uuid.UUID | None = None
    after_image_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)


class ImageMini(BaseModel):
    id: uuid.UUID
    title: str
    image_type: str
    taken_on: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ComparisonOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    treatment: str | None
    notes: str | None
    share_consent: bool
    share_consent_at: datetime | None
    created_at: datetime
    before: ImageMini
    after: ImageMini


async def _imagen(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, image_id: uuid.UUID) -> ClinicalImage:
    img = (
        await db.execute(select(ClinicalImage).where(ClinicalImage.id == image_id, ClinicalImage.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if img is None or img.patient_id != patient_id:
        raise HTTPException(status_code=422, detail="La imagen no pertenece a este paciente.")
    if img.archived_at is not None:
        raise HTTPException(status_code=422, detail="La imagen está archivada.")
    if not (img.mime_type or "").startswith("image/"):
        raise HTTPException(status_code=422, detail="Solo se pueden comparar fotos o radiografías en imagen (no PDF ni DICOM).")
    return img


async def _salida(db: AsyncSession, c: ImageComparison) -> ComparisonOut:
    antes = await db.get(ClinicalImage, c.before_image_id)
    despues = await db.get(ClinicalImage, c.after_image_id)
    return ComparisonOut(
        id=c.id, patient_id=c.patient_id, title=c.title, treatment=c.treatment, notes=c.notes,
        share_consent=c.share_consent, share_consent_at=c.share_consent_at, created_at=c.created_at,
        before=ImageMini.model_validate(antes), after=ImageMini.model_validate(despues),
    )


async def _get(db: AsyncSession, clinic_id: uuid.UUID, comparison_id: uuid.UUID) -> ImageComparison:
    c = (
        await db.execute(
            select(ImageComparison).where(ImageComparison.id == comparison_id, ImageComparison.clinic_id == clinic_id)
        )
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparación no encontrada")
    return c


def _consentimiento(c: ImageComparison, valor: bool | None, actor_id: uuid.UUID) -> None:
    if valor is None or valor == c.share_consent:
        return
    c.share_consent = valor
    c.share_consent_at = datetime.now(timezone.utc) if valor else None
    c.share_consent_by_id = actor_id if valor else None


patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/comparisons", tags=["imaging"])
router = APIRouter(prefix="/api/v1/comparisons", tags=["imaging"])


@patient_router.get("", response_model=list[ComparisonOut])
async def get_comparisons(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:read")),
):
    await get_patient_or_404(db, current_user.clinic_id, patient_id)
    filas = (
        await db.execute(
            select(ImageComparison)
            .where(ImageComparison.clinic_id == current_user.clinic_id, ImageComparison.patient_id == patient_id)
            .order_by(ImageComparison.created_at.desc())
        )
    ).scalars().all()
    return [await _salida(db, c) for c in filas]


@patient_router.post("", response_model=ComparisonOut, status_code=201)
async def post_comparison(
    patient_id: uuid.UUID,
    payload: ComparisonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:write")),
):
    await get_patient_or_404(db, current_user.clinic_id, patient_id)
    if payload.before_image_id == payload.after_image_id:
        raise HTTPException(status_code=422, detail="Elija dos imágenes distintas para el antes y el después.")
    await _imagen(db, current_user.clinic_id, patient_id, payload.before_image_id)
    await _imagen(db, current_user.clinic_id, patient_id, payload.after_image_id)
    c = ImageComparison(
        clinic_id=current_user.clinic_id, patient_id=patient_id,
        before_image_id=payload.before_image_id, after_image_id=payload.after_image_id,
        title=payload.title.strip(), treatment=payload.treatment, notes=payload.notes,
        created_at=datetime.now(timezone.utc), created_by_id=current_user.id,
    )
    _consentimiento(c, payload.share_consent, current_user.id)
    db.add(c)
    await db.flush()
    await record_audit(
        db, clinic_id=current_user.clinic_id, user_id=current_user.id, action="create", entity_type="image_comparison",
        entity_id=str(c.id), after=payload.model_dump(mode="json"),
    )
    out = await _salida(db, c)
    await db.commit()
    return out


@router.put("/{comparison_id}", response_model=ComparisonOut)
async def put_comparison(
    comparison_id: uuid.UUID,
    payload: ComparisonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:write")),
):
    c = await _get(db, current_user.clinic_id, comparison_id)
    data = payload.model_dump(exclude_unset=True)
    for campo in ("before_image_id", "after_image_id"):
        if data.get(campo):
            await _imagen(db, current_user.clinic_id, c.patient_id, data[campo])
            setattr(c, campo, data[campo])
    if c.before_image_id == c.after_image_id:
        raise HTTPException(status_code=422, detail="Elija dos imágenes distintas para el antes y el después.")
    if data.get("title"):
        c.title = data["title"].strip()
    for campo in ("treatment", "notes"):
        if campo in data:
            setattr(c, campo, data[campo])
    _consentimiento(c, data.get("share_consent"), current_user.id)
    await record_audit(
        db, clinic_id=current_user.clinic_id, user_id=current_user.id, action="update", entity_type="image_comparison",
        entity_id=str(c.id), after=payload.model_dump(exclude_unset=True, mode="json"),
    )
    out = await _salida(db, c)
    await db.commit()
    return out


@router.delete("/{comparison_id}", status_code=204)
async def delete_comparison(
    comparison_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("imaging:write")),
):
    """Borra solo la comparación: las fotos siguen en la historia clínica."""
    c = await _get(db, current_user.clinic_id, comparison_id)
    await record_audit(
        db, clinic_id=current_user.clinic_id, user_id=current_user.id, action="delete", entity_type="image_comparison",
        entity_id=str(c.id), after={"title": c.title},
    )
    await db.delete(c)
    await db.commit()
