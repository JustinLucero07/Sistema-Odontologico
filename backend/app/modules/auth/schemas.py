import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Solo se rellena para clientes que no son un navegador; ver el router.
    refresh_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class MeResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    is_superadmin: bool
    roles: list[str]
    permissions: list[str]
    confidentiality_required: bool = False
    # La contraseña actual es temporal (la puso un administrador).
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
