import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.payment_accounts.models import PaymentAccount
from app.modules.payment_accounts.schemas import AccountCreate, AccountUpdate

MAX_ACCOUNTS = 20


def _auditable(data: dict) -> dict:
    # La imagen no va a la auditoría: solo si se puso o se quitó.
    out = {k: v for k, v in data.items() if k != "qr_data"}
    if "qr_data" in data:
        out["qr"] = "cargado" if data["qr_data"] else "quitado"
    return out


async def list_accounts(db: AsyncSession, clinic_id: uuid.UUID, only_active: bool = False) -> list[PaymentAccount]:
    q = select(PaymentAccount).where(PaymentAccount.clinic_id == clinic_id)
    if only_active:
        q = q.where(PaymentAccount.is_active.is_(True))
    return list((await db.execute(q.order_by(PaymentAccount.sort_order, PaymentAccount.created_at))).scalars().all())


async def _get(db: AsyncSession, clinic_id: uuid.UUID, account_id: uuid.UUID) -> PaymentAccount:
    a = (
        await db.execute(
            select(PaymentAccount).where(PaymentAccount.id == account_id, PaymentAccount.clinic_id == clinic_id)
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta de pago no encontrada")
    return a


async def create_account(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: AccountCreate) -> PaymentAccount:
    total = await db.scalar(select(func.count()).select_from(PaymentAccount).where(PaymentAccount.clinic_id == clinic_id))
    if (total or 0) >= MAX_ACCOUNTS:
        raise HTTPException(status_code=422, detail=f"Máximo {MAX_ACCOUNTS} cuentas de pago.")
    orden = (await db.scalar(select(func.max(PaymentAccount.sort_order)).where(PaymentAccount.clinic_id == clinic_id)) or 0) + 1
    data = payload.model_dump()
    data["is_active"] = True if data.get("is_active") is None else data["is_active"]
    a = PaymentAccount(clinic_id=clinic_id, sort_order=orden, **data)
    db.add(a)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="payment_account",
        entity_id=str(a.id), after=_auditable(payload.model_dump(mode="json")),
    )
    return a


async def update_account(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, account_id: uuid.UUID, payload: AccountUpdate
) -> PaymentAccount:
    a = await _get(db, clinic_id, account_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is None and k in ("label", "is_active"):
            continue
        setattr(a, k, v)
    if not (a.qr_data or a.account_number or a.email):
        raise HTTPException(status_code=422, detail="La cuenta necesita el código QR o los datos de la cuenta.")
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="payment_account",
        entity_id=str(a.id), after=_auditable(payload.model_dump(exclude_unset=True, mode="json")),
    )
    return a


async def delete_account(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, account_id: uuid.UUID) -> None:
    a = await _get(db, clinic_id, account_id)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="payment_account",
        entity_id=str(a.id), after={"label": a.label},
    )
    await db.delete(a)


async def reorder(db: AsyncSession, clinic_id: uuid.UUID, ids: list[uuid.UUID]) -> list[PaymentAccount]:
    cuentas = {a.id: a for a in await list_accounts(db, clinic_id)}
    for i, aid in enumerate(ids, start=1):
        if aid in cuentas:
            cuentas[aid].sort_order = i
    await db.flush()
    return await list_accounts(db, clinic_id)
