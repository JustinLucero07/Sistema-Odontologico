import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.modules.users.models import RefreshToken, Role, User

settings = get_settings()


# After this many consecutive failures the account locks itself for a while.
# The per-IP rate limit does not cover a distributed attempt against ONE
# account, which is the shape an attack on a known clinician's email takes.
MAX_FAILED_LOGINS = 8
LOCKOUT_MINUTES = 15


async def authenticate(db: AsyncSession, email: str, password: str, ip_address: str | None) -> User:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.email == email.lower(), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user is not None and user.locked_until is not None and user.locked_until > now:
        remaining = int((user.locked_until - now).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Cuenta bloqueada por intentos fallidos. Vuelva a intentarlo en "
                f"{remaining} minuto(s)."
            ),
        )

    if user is None or not verify_password(password, user.hashed_password):
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_count = 0
                await record_audit(
                    db, clinic_id=user.clinic_id, user_id=user.id, action="lockout",
                    entity_type="user", entity_id=str(user.id), ip_address=ip_address,
                    after={"minutes": LOCKOUT_MINUTES},
                )
            await db.commit()
        # The same answer either way: saying "that account exists but the
        # password was wrong" tells an attacker which emails are real.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    await record_audit(
        db,
        clinic_id=user.clinic_id,
        user_id=user.id,
        action="login",
        entity_type="user",
        entity_id=str(user.id),
        ip_address=ip_address,
    )
    return user


def build_access_token(user: User) -> str:
    permissions = sorted({perm.code for role in user.roles for perm in role.permissions})
    return create_access_token(
        user_id=str(user.id),
        clinic_id=str(user.clinic_id),
        is_superadmin=user.is_superadmin,
        permissions=permissions,
    )


async def issue_refresh_token(
    db: AsyncSession, user: User, user_agent: str | None, ip_address: str | None
) -> str:
    raw_token, token_hash = generate_refresh_token()
    now = datetime.now(timezone.utc)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
    )
    return raw_token


async def rotate_refresh_token(
    db: AsyncSession, raw_token: str, user_agent: str | None, ip_address: str | None
) -> tuple[User, str]:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

    stored.revoked_at = now

    user_result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == stored.user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o inexistente")

    new_raw_token = await issue_refresh_token(db, user, user_agent, ip_address)
    return user, new_raw_token


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
