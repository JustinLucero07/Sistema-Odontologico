import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.payments import service
from app.modules.payments.constants import PAYMENT_METHODS
from app.modules.payments.schemas import (
    AccountStatement,
    CashSessionClose,
    CashSessionOpen,
    CashSessionOut,
    ChargeCreate,
    ChargeOut,
    DailyCashReport,
    InstallmentPlanCreate,
    PaymentCreate,
    PaymentOut,
    VoidRequest,
)

patient_router = APIRouter(prefix="/api/v1/patients/{patient_id}", tags=["payments"])
router = APIRouter(prefix="/api/v1/finance", tags=["payments"])


@router.get("/payment-methods")
async def get_payment_methods(
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return [
        {"code": code, "label": label, "requires_reference": needs}
        for code, label, needs in PAYMENT_METHODS
    ]


# ---- Patient account ----------------------------------------------------


@patient_router.get("/account", response_model=AccountStatement)
async def get_account(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.get_statement(db, current_user.clinic_id, patient_id)


@patient_router.post("/charges", response_model=ChargeOut, status_code=201)
async def post_charge(
    patient_id: uuid.UUID,
    payload: ChargeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    charge = await service.create_charge(
        db, current_user.clinic_id, current_user.id, patient_id, payload
    )
    await db.commit()
    return service._to_charge_out(charge, date.today())


@patient_router.post("/payments", response_model=PaymentOut, status_code=201)
async def post_payment(
    patient_id: uuid.UUID,
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    payment = await service.create_payment(
        db, current_user.clinic_id, current_user.id, patient_id, payload
    )
    await db.commit()
    return payment


# ---- Corrections --------------------------------------------------------


@router.post("/payments/{payment_id}/void", response_model=PaymentOut)
async def post_void_payment(
    payment_id: uuid.UUID,
    payload: VoidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    payment = await service.void_payment(
        db, current_user.clinic_id, current_user.id, payment_id, payload.reason
    )
    await db.commit()
    return payment


@router.post("/charges/{charge_id}/void", response_model=ChargeOut)
async def post_void_charge(
    charge_id: uuid.UUID,
    payload: VoidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    charge = await service.void_charge(
        db, current_user.clinic_id, current_user.id, charge_id, payload.reason
    )
    await db.commit()
    return service._to_charge_out(charge, date.today())


@router.post("/charges/{charge_id}/installments", response_model=ChargeOut)
async def post_installments(
    charge_id: uuid.UUID,
    payload: InstallmentPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    charge = await service.set_installment_plan(
        db, current_user.clinic_id, current_user.id, charge_id, payload
    )
    await db.commit()
    return service._to_charge_out(charge, date.today())


# ---- Till ---------------------------------------------------------------


@router.get("/cash-session", response_model=CashSessionOut | None)
async def get_cash_session(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.get_open_session(db, current_user.clinic_id)


@router.post("/cash-session/open", response_model=CashSessionOut, status_code=201)
async def post_open_cash_session(
    payload: CashSessionOpen,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    session = await service.open_session(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return session


@router.post("/cash-session/close", response_model=CashSessionOut)
async def post_close_cash_session(
    payload: CashSessionClose,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    session = await service.close_session(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return session


@router.get("/daily-report", response_model=DailyCashReport)
async def get_daily_report(
    day: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.daily_report(db, current_user.clinic_id, day or date.today())
