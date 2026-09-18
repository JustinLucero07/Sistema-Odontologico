import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.budgets.models import Budget, BudgetItem
from app.modules.budgets.schemas import BudgetCreate, BudgetItemCreate
from app.modules.patients.service import get_patient_or_404
from app.modules.treatment_plans.service import get_plan_or_404

# A budget only moves forward through this order; e.g. an "aceptado" budget
# can't silently flip back to "borrador".
_STATUS_ORDER = ["borrador", "enviado", "visto", "aceptado"]


def _budget_query():
    return select(Budget).options(selectinload(Budget.items))


async def list_budgets(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Budget]:
    await get_patient_or_404(db, clinic_id, patient_id)
    result = await db.execute(
        _budget_query()
        .where(Budget.clinic_id == clinic_id, Budget.patient_id == patient_id)
        .order_by(Budget.created_at.desc())
    )
    return list(result.scalars().all())


async def get_budget_or_404(db: AsyncSession, clinic_id: uuid.UUID, budget_id: uuid.UUID) -> Budget:
    result = await db.execute(_budget_query().where(Budget.id == budget_id, Budget.clinic_id == clinic_id))
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presupuesto no encontrado")
    return budget


async def create_budget(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: BudgetCreate
) -> Budget:
    await get_patient_or_404(db, clinic_id, patient_id)
    plan = await get_plan_or_404(db, clinic_id, payload.treatment_plan_id)
    if plan.patient_id != patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El plan no pertenece a este paciente")

    if payload.items is not None:
        item_payloads = payload.items
    else:
        item_payloads = [
            BudgetItemCreate(
                treatment_plan_item_id=item.id,
                description=item.treatment.name + (f" — pieza {item.fdi_number}" if item.fdi_number else ""),
                price=float(item.price),
                discount=float(item.discount),
                quantity=1,
            )
            for item in plan.items
            if item.status not in ("cancelado", "rechazado")
        ]

    budget = Budget(
        clinic_id=clinic_id, patient_id=patient_id, treatment_plan_id=plan.id, created_by_id=actor_id,
        tax_rate=payload.tax_rate, notes=payload.notes,
        items=[BudgetItem(clinic_id=clinic_id, **item.model_dump()) for item in item_payloads],
    )
    db.add(budget)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="budget",
        entity_id=str(budget.id), after={"patient_id": str(patient_id), "total": budget.total},
    )
    return await get_budget_or_404(db, clinic_id, budget.id)


async def update_status(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, budget_id: uuid.UUID, new_status: str
) -> Budget:
    budget = await get_budget_or_404(db, clinic_id, budget_id)

    if new_status == "rechazado":
        pass  # can be rejected from any non-final state
    elif budget.status in _STATUS_ORDER and new_status in _STATUS_ORDER:
        if _STATUS_ORDER.index(new_status) < _STATUS_ORDER.index(budget.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede retroceder de '{budget.status}' a '{new_status}'",
            )

    before_status = budget.status
    budget.status = new_status
    if new_status in ("aceptado", "rechazado"):
        budget.responded_at = datetime.now(timezone.utc)

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="budget",
        entity_id=str(budget_id), before={"status": before_status}, after={"status": new_status},
    )
    return budget
