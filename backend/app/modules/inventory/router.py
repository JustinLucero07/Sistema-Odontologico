import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.inventory import service
from app.modules.inventory.constants import MOVEMENT_REASONS, STOCK_UNITS
from app.modules.inventory.schemas import (
    ItemIn,
    ItemOut,
    MovementIn,
    MovementOut,
    StockAlerts,
    SupplierIn,
    SupplierOut,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/catalog")
async def get_catalog(
    current_user: CurrentUser = Depends(require_permission("inventory:read")),
):
    return {
        "units": [{"code": c, "label": l} for c, l in STOCK_UNITS],
        "reasons": [{"code": c, "label": l, "sign": s} for c, l, s in MOVEMENT_REASONS],
    }


@router.get("/suppliers", response_model=list[SupplierOut])
async def get_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:read")),
):
    return await service.list_suppliers(db, current_user.clinic_id)


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
async def post_supplier(
    payload: SupplierIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    supplier = await service.create_supplier(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return supplier


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
async def put_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    supplier = await service.update_supplier(db, current_user.clinic_id, current_user.id, supplier_id, payload)
    await db.commit()
    return supplier


@router.get("/items", response_model=list[ItemOut])
async def get_items(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:read")),
):
    return await service.list_items(
        db, current_user.clinic_id, include_inactive=include_inactive
    )


@router.post("/items", response_model=ItemOut, status_code=201)
async def post_item(
    payload: ItemIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    item = await service.create_item(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return service.to_item_out(item)


@router.put("/items/{item_id}", response_model=ItemOut)
async def put_item(
    item_id: uuid.UUID,
    payload: ItemIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    item = await service.update_item(db, current_user.clinic_id, current_user.id, item_id, payload)
    await db.commit()
    return service.to_item_out(item)


@router.post("/items/{item_id}/movements", response_model=ItemOut, status_code=201)
async def post_movement(
    item_id: uuid.UUID,
    payload: MovementIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    await service.record_movement(db, current_user.clinic_id, current_user.id, item_id, payload)
    await db.commit()
    # The item comes back with its recomputed stock, so the caller never has to
    # do the arithmetic itself.
    item = await service.get_item_or_404(db, current_user.clinic_id, item_id)
    return service.to_item_out(item)


@router.get("/movements", response_model=list[MovementOut])
async def get_movements(
    item_id: uuid.UUID | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:read")),
):
    return await service.list_movements(
        db, current_user.clinic_id, item_id=item_id, limit=limit
    )


@router.get("/alerts", response_model=StockAlerts)
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:read")),
):
    return await service.get_alerts(db, current_user.clinic_id)
