import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.core.security import hash_password
from app.modules.users.models import Permission, Role, User
from app.modules.users.schemas import RoleCreate, RoleUpdate, UserCreate, UserUpdate


async def list_users(db: AsyncSession, clinic_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.clinic_id == clinic_id, User.deleted_at.is_(None))
        .order_by(User.first_name)
    )
    return list(result.scalars().all())


async def get_user_or_404(db: AsyncSession, clinic_id: uuid.UUID, user_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id, User.clinic_id == clinic_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


async def _get_roles_by_ids(db: AsyncSession, clinic_id: uuid.UUID, role_ids: list[uuid.UUID]) -> list[Role]:
    if not role_ids:
        return []
    result = await db.execute(select(Role).where(Role.id.in_(role_ids), Role.clinic_id == clinic_id))
    roles = list(result.scalars().all())
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uno o más roles no existen")
    return roles


async def create_user(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: UserCreate
) -> User:
    existing = await db.execute(
        select(User).where(User.email == payload.email.lower(), User.clinic_id == clinic_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email")

    roles = await _get_roles_by_ids(db, clinic_id, payload.role_ids)
    user = User(
        clinic_id=clinic_id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        roles=roles,
    )
    db.add(user)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="user", entity_id=str(user.id),
        after={"email": user.email, "roles": [r.name for r in roles]},
    )
    return user


async def update_user(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, user_id: uuid.UUID, payload: UserUpdate
) -> User:
    user = await get_user_or_404(db, clinic_id, user_id)
    before = {"first_name": user.first_name, "last_name": user.last_name, "is_active": user.is_active}

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_ids is not None:
        user.roles = await _get_roles_by_ids(db, clinic_id, payload.role_ids)

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="user", entity_id=str(user.id),
        before=before,
        after={"first_name": user.first_name, "last_name": user.last_name, "is_active": user.is_active},
    )
    return user


async def deactivate_user(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, user_id: uuid.UUID) -> None:
    user = await get_user_or_404(db, clinic_id, user_id)
    user.is_active = False
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="deactivate", entity_type="user", entity_id=str(user.id),
    )


# --- Roles ---------------------------------------------------------------

async def list_roles(db: AsyncSession, clinic_id: uuid.UUID) -> list[Role]:
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.clinic_id == clinic_id)
        .order_by(Role.name)
    )
    return list(result.scalars().all())


async def _get_permissions_by_codes(db: AsyncSession, codes: list[str]) -> list[Permission]:
    if not codes:
        return []
    result = await db.execute(select(Permission).where(Permission.code.in_(codes)))
    permissions = list(result.scalars().all())
    if len(permissions) != len(set(codes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uno o más permisos no existen")
    return permissions


async def create_role(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: RoleCreate) -> Role:
    permissions = await _get_permissions_by_codes(db, payload.permission_codes)
    role = Role(clinic_id=clinic_id, name=payload.name, description=payload.description, permissions=permissions)
    db.add(role)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="role", entity_id=str(role.id),
        after={"name": role.name, "permissions": payload.permission_codes},
    )
    return role


async def get_role_or_404(db: AsyncSession, clinic_id: uuid.UUID, role_id: uuid.UUID) -> Role:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id, Role.clinic_id == clinic_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return role


async def update_role(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, role_id: uuid.UUID, payload: RoleUpdate
) -> Role:
    role = await get_role_or_404(db, clinic_id, role_id)
    if role.is_system and payload.permission_codes is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los roles base son un punto de partida: duplique el rol para personalizar sus permisos",
        )

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.permission_codes is not None:
        role.permissions = await _get_permissions_by_codes(db, payload.permission_codes)

    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="role", entity_id=str(role.id),
    )
    return role


async def delete_role(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, role_id: uuid.UUID) -> None:
    role = await get_role_or_404(db, clinic_id, role_id)
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar un rol base")
    await db.delete(role)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="role", entity_id=str(role_id),
    )


async def list_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    return list(result.scalars().all())
