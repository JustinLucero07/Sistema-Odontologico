import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.cartera import service
from app.modules.cartera.schemas import Portfolio, Projection, RecurringIn, RecurringOut, RegisterRecurring
from app.modules.expenses.schemas import ExpenseOut

router = APIRouter(prefix="/api/v1/finance", tags=["cartera"])


@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    """Cartera completa: saldo de cada paciente, cargos abiertos y pagados, y
    tratamientos en curso o planificados de todos los pacientes."""
    return await service.portfolio(db, current_user.clinic_id)


@router.get("/projection", response_model=Projection)
async def get_projection(
    days: int = Query(default=30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    """Lo que debería entrar (cuotas por vencer) y salir (gastos fijos)."""
    return await service.projection(db, current_user.clinic_id, days)


@router.get("/recurring-expenses", response_model=list[RecurringOut])
async def get_recurring(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.list_recurring(db, current_user.clinic_id)


@router.post("/recurring-expenses", response_model=RecurringOut, status_code=201)
async def post_recurring(
    payload: RecurringIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.save_recurring(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return out


@router.put("/recurring-expenses/{rid}", response_model=RecurringOut)
async def put_recurring(
    rid: uuid.UUID,
    payload: RecurringIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.save_recurring(db, current_user.clinic_id, current_user.id, payload, rid)
    await db.commit()
    return out


@router.delete("/recurring-expenses/{rid}", status_code=204)
async def del_recurring(
    rid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    await service.delete_recurring(db, current_user.clinic_id, current_user.id, rid)
    await db.commit()


@router.post("/recurring-expenses/{rid}/register", response_model=ExpenseOut, status_code=201)
async def register_recurring(
    rid: uuid.UUID,
    payload: RegisterRecurring,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    out = await service.register_recurring(db, current_user.clinic_id, current_user.id, rid, payload)
    await db.commit()
    return out
