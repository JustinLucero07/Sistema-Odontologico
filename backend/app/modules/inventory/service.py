import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.inventory.constants import MOVEMENT_SIGN, quantity
from app.modules.inventory.models import InventoryItem, StockMovement, Supplier
from app.modules.inventory.schemas import ItemIn, ItemOut, MovementIn, StockAlerts, SupplierIn

ZERO = Decimal("0.000")
# How far ahead an expiry counts as "coming up" on the alerts board.
EXPIRY_HORIZON_DAYS = 60


# ---- Suppliers ----------------------------------------------------------


async def list_suppliers(db: AsyncSession, clinic_id: uuid.UUID) -> list[Supplier]:
    result = await db.execute(
        select(Supplier).where(Supplier.clinic_id == clinic_id).order_by(Supplier.name)
    )
    return list(result.scalars().all())


async def create_supplier(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: SupplierIn
) -> Supplier:
    supplier = Supplier(clinic_id=clinic_id, **payload.model_dump())
    db.add(supplier)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="supplier",
        entity_id=str(supplier.id), after={"name": supplier.name},
    )
    return supplier


async def update_supplier(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierIn
) -> Supplier:
    supplier = (
        await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    for field, value in payload.model_dump().items():
        setattr(supplier, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="supplier",
        entity_id=str(supplier_id), after=payload.model_dump(mode="json"),
    )
    return supplier


# ---- Items --------------------------------------------------------------


async def get_item_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, item_id: uuid.UUID
) -> InventoryItem:
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.movements), selectinload(InventoryItem.supplier))
        .where(InventoryItem.id == item_id, InventoryItem.clinic_id == clinic_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    return item


def _on_hand(item: InventoryItem) -> Decimal:
    """Stock is the SUM of the ledger, computed here rather than stored.

    Nothing caches this: the moment a total lives in a column, a correction or
    a concurrent entry puts it out of step with the movements that produced
    it, and there is no way to tell afterwards which one lied."""
    return quantity(sum((m.quantity * m.sign for m in item.movements), ZERO))


def _lot_balances(item: InventoryItem) -> dict[tuple[str | None, date | None], Decimal]:
    """Stock per lot, so an expiry date can be tied to a real remaining amount
    instead of flagging a lot that was already used up."""
    balances: dict[tuple[str | None, date | None], Decimal] = {}
    for movement in item.movements:
        key = (movement.lot_number, movement.expires_on)
        balances[key] = balances.get(key, ZERO) + movement.quantity * movement.sign
    return {k: quantity(v) for k, v in balances.items() if v > 0}


def to_item_out(item: InventoryItem, today: date | None = None) -> ItemOut:
    today = today or date.today()
    on_hand = _on_hand(item)
    balances = _lot_balances(item)
    dated = [(expiry, qty) for (_lot, expiry), qty in balances.items() if expiry is not None]

    return ItemOut(
        id=item.id,
        name=item.name,
        sku=item.sku,
        category=item.category,
        unit=item.unit,
        supplier_id=item.supplier_id,
        supplier_name=item.supplier.name if item.supplier else None,
        minimum_stock=quantity(item.minimum_stock),
        unit_cost=item.unit_cost,
        is_active=item.is_active,
        notes=item.notes,
        on_hand=on_hand,
        # An inactive item is not reordered, so it never raises the alarm.
        below_minimum=item.is_active and on_hand < quantity(item.minimum_stock),
        next_expiry=min((e for e, _ in dated), default=None),
        expired_quantity=quantity(sum((q for e, q in dated if e < today), ZERO)),
    )


async def list_items(
    db: AsyncSession, clinic_id: uuid.UUID, *, include_inactive: bool = False
) -> list[ItemOut]:
    query = (
        select(InventoryItem)
        .options(selectinload(InventoryItem.movements), selectinload(InventoryItem.supplier))
        .where(InventoryItem.clinic_id == clinic_id)
    )
    if not include_inactive:
        query = query.where(InventoryItem.is_active.is_(True))
    result = await db.execute(query.order_by(InventoryItem.name))
    return [to_item_out(item) for item in result.scalars().all()]


async def create_item(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: ItemIn
) -> InventoryItem:
    item = InventoryItem(
        clinic_id=clinic_id, created_at=datetime.now(timezone.utc), **payload.model_dump()
    )
    db.add(item)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="inventory_item",
        entity_id=str(item.id), after={"name": item.name, "unit": item.unit},
    )
    return await get_item_or_404(db, clinic_id, item.id)


async def update_item(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, item_id: uuid.UUID, payload: ItemIn
) -> InventoryItem:
    item = await get_item_or_404(db, clinic_id, item_id)
    before = {"name": item.name, "minimum_stock": str(item.minimum_stock)}
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="inventory_item",
        entity_id=str(item_id), before=before,
        after={"name": item.name, "minimum_stock": str(item.minimum_stock)},
    )
    return await get_item_or_404(db, clinic_id, item_id)


# ---- Movements ----------------------------------------------------------


async def record_movement(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: MovementIn,
) -> StockMovement:
    item = await get_item_or_404(db, clinic_id, item_id)
    sign = MOVEMENT_SIGN[payload.reason]
    amount = quantity(payload.quantity)

    if sign < 0:
        on_hand = _on_hand(item)
        # Refusing to go negative is the point of a ledger: a count below zero
        # is not a small error, it means the records and the shelf disagree and
        # someone has to look at the shelf.
        if amount > on_hand:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"No hay existencias suficientes de «{item.name}»: "
                    f"quedan {on_hand} {item.unit} y se intentan retirar {amount}."
                ),
            )

    movement = StockMovement(
        clinic_id=clinic_id,
        item_id=item_id,
        reason=payload.reason,
        quantity=amount,
        sign=sign,
        unit_cost=payload.unit_cost,
        lot_number=payload.lot_number,
        expires_on=payload.expires_on,
        patient_id=payload.patient_id,
        notes=payload.notes,
        created_by_id=actor_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="stock_movement",
        entity_id=str(movement.id),
        after={"item": item.name, "reason": payload.reason, "quantity": str(amount * sign)},
    )
    return movement


async def list_movements(
    db: AsyncSession, clinic_id: uuid.UUID, *, item_id: uuid.UUID | None = None, limit: int = 200
) -> list[dict]:
    query = (
        select(StockMovement, InventoryItem.name)
        .join(InventoryItem, StockMovement.item_id == InventoryItem.id)
        .where(StockMovement.clinic_id == clinic_id)
    )
    if item_id is not None:
        query = query.where(StockMovement.item_id == item_id)
    result = await db.execute(query.order_by(StockMovement.created_at.desc()).limit(limit))
    return [
        {
            "id": m.id,
            "item_id": m.item_id,
            "item_name": name,
            "reason": m.reason,
            "quantity": quantity(m.quantity),
            "sign": m.sign,
            "unit_cost": m.unit_cost,
            "lot_number": m.lot_number,
            "expires_on": m.expires_on,
            "patient_id": m.patient_id,
            "notes": m.notes,
            "created_by_id": m.created_by_id,
            "created_at": m.created_at,
        }
        for m, name in result.all()
    ]


async def get_alerts(db: AsyncSession, clinic_id: uuid.UUID) -> StockAlerts:
    today = date.today()
    horizon = today + timedelta(days=EXPIRY_HORIZON_DAYS)
    items = await list_items(db, clinic_id)

    return StockAlerts(
        below_minimum=[i for i in items if i.below_minimum],
        expiring_soon=[
            i
            for i in items
            if i.next_expiry is not None and today <= i.next_expiry <= horizon
        ],
        expired=[i for i in items if i.expired_quantity > ZERO],
    )
