import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.patients.service import get_patient_or_404
from app.modules.treatment_plans.models import TreatmentPlan, TreatmentPlanItem
from app.modules.treatment_plans.schemas import (
    TreatmentPlanCreate,
    TreatmentPlanItemCreate,
    TreatmentPlanItemUpdate,
    TreatmentPlanUpdate,
)
from app.modules.treatments.service import get_treatment_or_404


def _plan_query():
    return select(TreatmentPlan).options(
        selectinload(TreatmentPlan.items).selectinload(TreatmentPlanItem.treatment)
    )


async def list_plans(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[TreatmentPlan]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        _plan_query()
        .where(TreatmentPlan.clinic_id == clinic_id, TreatmentPlan.patient_id == patient_id)
        .order_by(TreatmentPlan.created_at.desc())
    )
    return list(result.scalars().all())


async def get_plan_or_404(db: AsyncSession, clinic_id: uuid.UUID, plan_id: uuid.UUID) -> TreatmentPlan:
    result = await db.execute(_plan_query().where(TreatmentPlan.id == plan_id, TreatmentPlan.clinic_id == clinic_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan de tratamiento no encontrado")
    return plan


async def _build_item(db: AsyncSession, clinic_id: uuid.UUID, payload: TreatmentPlanItemCreate) -> TreatmentPlanItem:
    await get_treatment_or_404(db, clinic_id, payload.treatment_id)
    return TreatmentPlanItem(clinic_id=clinic_id, **payload.model_dump())


async def create_plan(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: TreatmentPlanCreate
) -> TreatmentPlan:
    await get_patient_or_404(db, clinic_id, patient_id)
    items = [await _build_item(db, clinic_id, item) for item in payload.items]

    plan = TreatmentPlan(
        clinic_id=clinic_id, patient_id=patient_id, created_by_id=actor_id,
        title=payload.title, notes=payload.notes, items=items,
    )
    db.add(plan)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="treatment_plan",
        entity_id=str(plan.id), after={"patient_id": str(patient_id), "items": len(items)},
    )
    return await get_plan_or_404(db, clinic_id, plan.id)


async def add_item(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, plan_id: uuid.UUID, payload: TreatmentPlanItemCreate
) -> TreatmentPlan:
    plan = await get_plan_or_404(db, clinic_id, plan_id)
    item = await _build_item(db, clinic_id, payload)
    item.plan_id = plan.id
    db.add(item)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="treatment_plan_item",
        entity_id=str(item.id), after={"plan_id": str(plan_id)},
    )
    return await get_plan_or_404(db, clinic_id, plan_id)


async def update_plan(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, plan_id: uuid.UUID,
    payload: TreatmentPlanUpdate,
) -> TreatmentPlan:
    plan = await get_plan_or_404(db, clinic_id, plan_id)
    before = {"title": plan.title, "notes": plan.notes}
    plan.title = payload.title
    plan.notes = payload.notes
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="treatment_plan",
        entity_id=str(plan_id), before=before, after=payload.model_dump(),
    )
    return await get_plan_or_404(db, clinic_id, plan_id)


async def update_item(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, plan_id: uuid.UUID, item_id: uuid.UUID,
    payload: TreatmentPlanItemUpdate,
) -> TreatmentPlan:
    plan = await get_plan_or_404(db, clinic_id, plan_id)
    item = next((i for i in plan.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem del plan no encontrado")

    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "completado" and item.completed_date is None and "completed_date" not in data:
        data["completed_date"] = date.today()

    for field, value in data.items():
        setattr(item, field, value)

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="treatment_plan_item",
        entity_id=str(item_id), after=data,
    )
    return await get_plan_or_404(db, clinic_id, plan_id)
