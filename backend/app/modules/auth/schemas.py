import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    is_superadmin: bool
    roles: list[str]
    permissions: list[str]
