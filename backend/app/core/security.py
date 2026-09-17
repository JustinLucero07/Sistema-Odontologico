import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, user_id: str, clinic_id: str, is_superadmin: bool, permissions: list[str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "clinic_id": clinic_id,
        "is_superadmin": is_superadmin,
        "permissions": permissions,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). Only the hash is persisted — the raw value
    is handed to the client once and can never be recovered from the database."""
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_refresh_token(raw_token)
    return raw_token, token_hash


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
