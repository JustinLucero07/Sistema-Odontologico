import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.inventory.constants import (
    MAX_QUANTITY,
    MOVEMENT_REASON_CODES,
    STOCK_UNIT_CODES,
    quantity,
)


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    is_active: bool = True


class SupplierOut(SupplierIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=80)
    unit: str = "unidad"
    supplier_id: uuid.UUID | None = None
    minimum_stock: Decimal = Field(ge=0, le=MAX_QUANTITY, default=Decimal("0"))
    unit_cost: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    is_active: bool = True

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        if value not in STOCK_UNIT_CODES:
            raise ValueError(f"Unidad inválida: {value}")
        return value

    @field_validator("minimum_stock")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return quantity(value)


class ItemOut(BaseModel):
    id: uuid.UUID
    name: str
    sku: str | None
    category: str | None
    unit: str
    supplier_id: uuid.UUID | None
    supplier_name: str | None
    minimum_stock: Decimal
    unit_cost: Decimal | None
    is_active: bool
    notes: str | None
    # Derived from the movement ledger on every read, never stored.
    on_hand: Decimal
    below_minimum: bool
    # Earliest expiry still in stock, so the reorder list can flag it.
    next_expiry: date | None
    expired_quantity: Decimal


class MovementIn(BaseModel):
    reason: str
    # Always positive. The reason decides the direction; see MOVEMENT_SIGN.
    quantity: Decimal = Field(gt=0, le=MAX_QUANTITY)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    lot_number: str | None = Field(default=None, max_length=80)
    expires_on: date | None = None
    patient_id: uuid.UUID | None = None
    notes: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if value not in MOVEMENT_REASON_CODES:
            raise ValueError(f"Motivo de movimiento inválido: {value}")
        return value

    @field_validator("quantity")
    @classmethod
    def quantize(cls, value: Decimal) -> Decimal:
        return quantity(value)


class MovementOut(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    item_name: str
    reason: str
    quantity: Decimal
    sign: int
    unit_cost: Decimal | None
    lot_number: str | None
    expires_on: date | None
    patient_id: uuid.UUID | None
    notes: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime


class StockAlerts(BaseModel):
    """The two questions a clinic asks its inventory each morning."""

    below_minimum: list[ItemOut]
    expiring_soon: list[ItemOut]
    expired: list[ItemOut]
