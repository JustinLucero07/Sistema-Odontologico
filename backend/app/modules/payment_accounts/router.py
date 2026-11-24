import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.modules.payment_accounts import service
from app.modules.payment_accounts.schemas import AccountCreate, AccountOut, AccountUpdate, Reorder

router = APIRouter(prefix="/api/v1/payment-accounts", tags=["payment-accounts"])


@router.get("", response_model=list[AccountOut])
async def get_accounts(
    all: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    ver_todas = all and current_user.has_permission("settings:manage")
    return await service.list_accounts(db, current_user.clinic_id, only_active=not ver_todas)


@router.post("", response_model=AccountOut, status_code=201)
async def post_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    a = await service.create_account(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return a


@router.put("/{account_id}", response_model=AccountOut)
async def put_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    a = await service.update_account(db, current_user.clinic_id, current_user.id, account_id, payload)
    await db.commit()
    return a


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    await service.delete_account(db, current_user.clinic_id, current_user.id, account_id)
    await db.commit()


@router.post("/reorder", response_model=list[AccountOut])
async def post_reorder(
    payload: Reorder,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.reorder(db, current_user.clinic_id, payload.ids)
    await db.commit()
    return out
