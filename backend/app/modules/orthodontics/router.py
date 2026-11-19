import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.clinics.service import get_clinic_or_404
from app.modules.orthodontics import export, service
from app.modules.orthodontics.constants import (
    APPLIANCES,
    CASE_STATUSES,
    DOC_FIELDS,
    DOC_STATUSES,
    STAGES,
    TAD_OPTIONS,
)
from app.modules.orthodontics.schemas import (
    CaseCreate,
    CaseDetail,
    CaseList,
    CaseOut,
    CaseUpdate,
    ControlCreate,
    ControlPayment,
    ControlsGenerate,
    ControlUpdate,
)

router = APIRouter(prefix="/api/v1/orthodontics", tags=["orthodontics"])
patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/orthodontics", tags=["orthodontics"])

LEER = "orthodontics:read"
ESCRIBIR = "orthodontics:write"


@router.get("/options")
async def get_options(current_user: CurrentUser = Depends(require_permission(LEER))):
    par = lambda lista: [{"code": c, "label": l} for c, l in lista]  # noqa: E731
    return {
        "statuses": par(CASE_STATUSES),
        "tad": par(TAD_OPTIONS),
        "doc_statuses": par(DOC_STATUSES),
        "doc_fields": par(DOC_FIELDS),
        "appliances": APPLIANCES,
        "stages": STAGES,
    }


@router.get("/cases", response_model=CaseList)
async def get_cases(
    q: str | None = Query(None, max_length=120),
    status: str | None = Query(None),
    has_tad: str | None = Query(None),
    docs: str | None = Query(None),
    next_control: str | None = Query(None),
    special_attention: bool | None = Query(None),
    needs_review: bool | None = Query(None),
    professional_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(LEER)),
):
    return await service.list_cases(
        db, current_user.clinic_id, q=q, status_=status, has_tad=has_tad, docs=docs, next_control=next_control,
        special_attention=special_attention, needs_review=needs_review, professional_id=professional_id,
    )


@router.post("/cases", response_model=CaseDetail, status_code=201)
async def post_case(
    payload: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    out = await service.create_case(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return out


@router.get("/cases/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(LEER)),
):
    return await service.get_case(db, current_user.clinic_id, case_id)


@router.patch("/cases/{case_id}", response_model=CaseDetail)
async def patch_case(
    case_id: uuid.UUID,
    payload: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    out = await service.update_case(db, current_user.clinic_id, current_user.id, case_id, payload)
    await db.commit()
    return out


@router.delete("/cases/{case_id}", status_code=204)
async def delete_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    await service.delete_case(db, current_user.clinic_id, current_user.id, case_id)
    await db.commit()


@router.post("/cases/{case_id}/controls", response_model=CaseDetail, status_code=201)
async def post_control(
    case_id: uuid.UUID,
    payload: ControlCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    out = await service.add_control(db, current_user.clinic_id, current_user.id, case_id, payload)
    await db.commit()
    return out


@router.post("/cases/{case_id}/controls/generate", response_model=CaseDetail, status_code=201)
async def post_generate(
    case_id: uuid.UUID,
    payload: ControlsGenerate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    out = await service.generate_controls(db, current_user.clinic_id, current_user.id, case_id, payload)
    await db.commit()
    return out


@router.patch("/controls/{control_id}", response_model=CaseDetail)
async def patch_control(
    control_id: uuid.UUID,
    payload: ControlUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    out = await service.update_control(db, current_user.clinic_id, current_user.id, control_id, payload)
    await db.commit()
    return out


@router.delete("/controls/{control_id}", response_model=CaseDetail)
async def delete_control(
    control_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(ESCRIBIR)),
):
    out = await service.delete_control(db, current_user.clinic_id, current_user.id, control_id)
    await db.commit()
    return out


@router.post("/controls/{control_id}/payments", response_model=CaseDetail, status_code=201)
async def post_control_payment(
    control_id: uuid.UUID,
    payload: ControlPayment,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.pay_control(db, current_user.clinic_id, current_user.id, control_id, payload)
    await db.commit()
    return out


@router.get("/cases/{case_id}/export.csv")
async def export_csv(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(LEER)),
):
    case = await service.get_case(db, current_user.clinic_id, case_id)
    return Response(
        content=export.to_csv(case), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ortodoncia-{case.code}.csv"'},
    )


@router.get("/cases/{case_id}/export.pdf")
async def export_pdf(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(LEER)),
):
    case = await service.get_case(db, current_user.clinic_id, case_id)
    clinic = await get_clinic_or_404(db, current_user.clinic_id)
    return Response(
        content=export.to_pdf(case, clinic.name), media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="ortodoncia-{case.code}.pdf"'},
    )


@patient_router.get("", response_model=list[CaseOut])
async def get_patient_cases(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(LEER)),
):
    return await service.cases_for_patient(db, current_user.clinic_id, patient_id)
