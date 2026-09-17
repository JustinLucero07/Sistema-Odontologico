import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.modules.users.models import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Resolved principal for the request: the user row plus the flattened
    set of permission codes granted by all of their roles."""

    def __init__(self, user: User, permissions: set[str]):
        self.user = user
        self.id: uuid.UUID = user.id
        self.clinic_id: uuid.UUID = user.clinic_id
        self.is_superadmin: bool = user.is_superadmin
        self.permissions = permissions

    def has_permission(self, code: str) -> bool:
        return self.is_superadmin or code in self.permissions


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o inexistente")

    # Permissions are re-read from the database on every request (not trusted from
    # the JWT) so a revoked role takes effect immediately, without waiting for the
    # access token to expire.
    permissions = {perm.code for role in user.roles for perm in role.permissions}
    request.state.clinic_id = user.clinic_id
    return CurrentUser(user=user, permissions=permissions)


def require_permission(code: str):
    async def checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_permission(code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene el permiso requerido: {code}",
            )
        return current_user

    return checker
