import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.credits import service
from app.modules.credits.constants import FREQUENCIES, FREQUENCY_DAYS, MAX_INSTALLMENTS, MAX_MONTHLY_RATE
from app.modules.credits.schemas import (
    CreditCreate,
    CreditDetail,
    CreditOut,
    CreditPayment,
    CreditRestructure,
    CreditSummary,
    CreditUpdate,
    Preview,
)
from app.shared.voiding import VoidRequest

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])
patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}/credits", tags=["credits"])


@router.get("/options")
async def get_options(current_user: CurrentUser = Depends(require_permission("payments:read"))):
    return {
        "frequencies": [{"code": c, "label": l, "days": d} for c, l, d in FREQUENCIES],
        "max_installments": MAX_INSTALLMENTS,
        "max_monthly_rate": MAX_MONTHLY_RATE,
    }


@router.get("/preview", response_model=Preview)
async def get_preview(
    principal: Decimal = Query(gt=0),
    installment_count: int = Query(ge=1, le=MAX_INSTALLMENTS),
    monthly_rate: Decimal = Query(Decimal("0"), ge=0, le=MAX_MONTHLY_RATE),
    frequency: str = Query("mensual"),
    first_due_on: date = Query(...),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    if frequency not in FREQUENCY_DAYS:
        frequency = "mensual"
    return service.preview(principal, installment_count, monthly_rate, frequency, first_due_on)


@router.get("/summary", response_model=CreditSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.summary(db, current_user.clinic_id)


@router.get("", response_model=list[CreditOut])
async def get_credits(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.list_credits(db, current_user.clinic_id, state=status)


@router.get("/{credit_id}", response_model=CreditDetail)
async def get_credit(
    credit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.get_credit(db, current_user.clinic_id, credit_id)


@router.put("/{credit_id}", response_model=CreditDetail)
async def put_credit(
    credit_id: uuid.UUID,
    payload: CreditUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.update_credit(db, current_user.clinic_id, current_user.id, credit_id, payload)
    await db.commit()
    return out


@router.post("/{credit_id}/payments", response_model=CreditDetail, status_code=201)
async def post_payment(
    credit_id: uuid.UUID,
    payload: CreditPayment,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.pay(db, current_user.clinic_id, current_user.id, credit_id, payload)
    await db.commit()
    return out


@router.post("/{credit_id}/restructure", response_model=CreditDetail)
async def post_restructure(
    credit_id: uuid.UUID,
    payload: CreditRestructure,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.restructure(db, current_user.clinic_id, current_user.id, credit_id, payload)
    await db.commit()
    return out


@router.post("/{credit_id}/void", response_model=CreditDetail)
async def post_void(
    credit_id: uuid.UUID,
    payload: VoidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.void_credit(db, current_user.clinic_id, current_user.id, credit_id, payload.reason)
    await db.commit()
    return out


@patient_router.get("", response_model=list[CreditOut])
async def get_patient_credits(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.list_credits(db, current_user.clinic_id, patient_id=patient_id)


@patient_router.post("", response_model=CreditDetail, status_code=201)
async def post_credit(
    patient_id: uuid.UUID,
    payload: CreditCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.create_credit(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return out
