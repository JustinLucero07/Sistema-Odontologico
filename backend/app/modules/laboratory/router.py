import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.laboratory import service
from app.modules.laboratory.constants import LAB_ORDER_STATUSES, LAB_WORK_TYPES
from app.modules.laboratory.schemas import (
    LabOrderCreate,
    LabOrderOut,
    LabOrderStatusUpdate,
    LabOrderUpdate,
    LaboratoryIn,
    LaboratoryOut,
)

router = APIRouter(prefix="/api/v1/laboratory", tags=["laboratory"])


@router.get("/catalog")
async def get_catalog(
    current_user: CurrentUser = Depends(require_permission("laboratory:read")),
):
    return {
        "statuses": [{"code": c, "label": l} for c, l in LAB_ORDER_STATUSES],
        "work_types": [{"code": c, "label": l} for c, l in LAB_WORK_TYPES],
    }


@router.get("/laboratories", response_model=list[LaboratoryOut])
async def get_laboratories(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:read")),
):
    return await service.list_laboratories(db, current_user.clinic_id)


@router.post("/laboratories", response_model=LaboratoryOut, status_code=201)
async def post_laboratory(
    payload: LaboratoryIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:write")),
):
    lab = await service.create_laboratory(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return lab


@router.put("/laboratories/{laboratory_id}", response_model=LaboratoryOut)
async def put_laboratory(
    laboratory_id: uuid.UUID,
    payload: LaboratoryIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:write")),
):
    lab = await service.update_laboratory(db, current_user.clinic_id, current_user.id, laboratory_id, payload)
    await db.commit()
    return lab


@router.get("/orders", response_model=list[LabOrderOut])
async def get_orders(
    patient_id: uuid.UUID | None = Query(None),
    open_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:read")),
):
    return await service.list_orders(
        db, current_user.clinic_id, patient_id=patient_id, open_only=open_only
    )


@router.post("/orders", response_model=LabOrderOut, status_code=201)
async def post_order(
    payload: LabOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:write")),
):
    order = await service.create_order(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return order


@router.put("/orders/{order_id}", response_model=LabOrderOut)
async def put_order(
    order_id: uuid.UUID,
    payload: LabOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:write")),
):
    order = await service.update_order(db, current_user.clinic_id, current_user.id, order_id, payload)
    await db.commit()
    return order


@router.put("/orders/{order_id}/status", response_model=LabOrderOut)
async def put_order_status(
    order_id: uuid.UUID,
    payload: LabOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("laboratory:write")),
):
    order = await service.update_status(
        db, current_user.clinic_id, current_user.id, order_id, payload
    )
    await db.commit()
    return order
