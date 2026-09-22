import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.treatment_plans import service
from app.modules.treatment_plans.schemas import (
    TreatmentPlanCreate,
    TreatmentPlanItemCreate,
    TreatmentPlanItemUpdate,
    TreatmentPlanOut,
    TreatmentPlanUpdate,
)

patient_plans_router = APIRouter(prefix="/api/v1/patients/{patient_id}/treatment-plans", tags=["treatment-plans"])
plans_router = APIRouter(prefix="/api/v1/treatment-plans", tags=["treatment-plans"])


@patient_plans_router.get("", response_model=list[TreatmentPlanOut])
async def get_plans(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:read")),
):
    plans = await service.list_plans(db, current_user.clinic_id, patient_id)
    return [TreatmentPlanOut.from_plan(p) for p in plans]


@patient_plans_router.post("", response_model=TreatmentPlanOut, status_code=201)
async def post_plan(
    patient_id: uuid.UUID,
    payload: TreatmentPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:write")),
):
    plan = await service.create_plan(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return TreatmentPlanOut.from_plan(plan)


@plans_router.get("/{plan_id}", response_model=TreatmentPlanOut)
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:read")),
):
    plan = await service.get_plan_or_404(db, current_user.clinic_id, plan_id)
    return TreatmentPlanOut.from_plan(plan)


@plans_router.put("/{plan_id}", response_model=TreatmentPlanOut)
async def put_plan(
    plan_id: uuid.UUID,
    payload: TreatmentPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:write")),
):
    plan = await service.update_plan(db, current_user.clinic_id, current_user.id, plan_id, payload)
    await db.commit()
    return TreatmentPlanOut.from_plan(plan)


@plans_router.post("/{plan_id}/items", response_model=TreatmentPlanOut, status_code=201)
async def post_plan_item(
    plan_id: uuid.UUID,
    payload: TreatmentPlanItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:write")),
):
    plan = await service.add_item(db, current_user.clinic_id, current_user.id, plan_id, payload)
    await db.commit()
    return TreatmentPlanOut.from_plan(plan)


@plans_router.put("/{plan_id}/items/{item_id}", response_model=TreatmentPlanOut)
async def put_plan_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: TreatmentPlanItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("treatments:write")),
):
    plan = await service.update_item(db, current_user.clinic_id, current_user.id, plan_id, item_id, payload)
    await db.commit()
    return TreatmentPlanOut.from_plan(plan)
