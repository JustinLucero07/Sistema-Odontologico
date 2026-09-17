import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.users import service
from app.modules.users.schemas import (
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/permissions", response_model=list[PermissionOut])
async def get_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("roles:manage")),
):
    return await service.list_permissions(db)


@router.get("/roles", response_model=list[RoleOut])
async def get_roles(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("roles:manage")),
):
    return await service.list_roles(db, current_user.clinic_id)


@router.post("/roles", response_model=RoleOut, status_code=201)
async def post_role(
    payload: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("roles:manage")),
):
    role = await service.create_role(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return await service.get_role_or_404(db, current_user.clinic_id, role.id)


@router.put("/roles/{role_id}", response_model=RoleOut)
async def put_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("roles:manage")),
):
    role = await service.update_role(db, current_user.clinic_id, current_user.id, role_id, payload)
    await db.commit()
    return await service.get_role_or_404(db, current_user.clinic_id, role.id)


@router.delete("/roles/{role_id}", status_code=204)
async def remove_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("roles:manage")),
):
    await service.delete_role(db, current_user.clinic_id, current_user.id, role_id)
    await db.commit()


@router.get("/users", response_model=list[UserOut])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("users:manage")),
):
    return await service.list_users(db, current_user.clinic_id)


@router.post("/users", response_model=UserOut, status_code=201)
async def post_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("users:manage")),
):
    user = await service.create_user(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return await service.get_user_or_404(db, current_user.clinic_id, user.id)


@router.put("/users/{user_id}", response_model=UserOut)
async def put_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("users:manage")),
):
    user = await service.update_user(db, current_user.clinic_id, current_user.id, user_id, payload)
    await db.commit()
    return await service.get_user_or_404(db, current_user.clinic_id, user.id)


@router.delete("/users/{user_id}", status_code=204)
async def remove_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("users:manage")),
):
    await service.deactivate_user(db, current_user.clinic_id, current_user.id, user_id)
    await db.commit()
