import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.budgets import service
from app.modules.budgets.schemas import BudgetCreate, BudgetOut, BudgetStatusUpdate

patient_budgets_router = APIRouter(prefix="/api/v1/patients/{patient_id}/budgets", tags=["budgets"])
budgets_router = APIRouter(prefix="/api/v1/budgets", tags=["budgets"])


@patient_budgets_router.get("", response_model=list[BudgetOut])
async def get_budgets(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("budgets:read")),
):
    budgets = await service.list_budgets(db, current_user.clinic_id, patient_id)
    return [BudgetOut.from_budget(b) for b in budgets]


@patient_budgets_router.post("", response_model=BudgetOut, status_code=201)
async def post_budget(
    patient_id: uuid.UUID,
    payload: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("budgets:write")),
):
    budget = await service.create_budget(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return BudgetOut.from_budget(budget)


@budgets_router.get("/{budget_id}", response_model=BudgetOut)
async def get_budget(
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("budgets:read")),
):
    budget = await service.get_budget_or_404(db, current_user.clinic_id, budget_id)
    return BudgetOut.from_budget(budget)


@budgets_router.put("/{budget_id}/status", response_model=BudgetOut)
async def put_budget_status(
    budget_id: uuid.UUID,
    payload: BudgetStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("budgets:write")),
):
    budget = await service.update_status(db, current_user.clinic_id, current_user.id, budget_id, payload.status)
    await db.commit()
    return BudgetOut.from_budget(budget)
