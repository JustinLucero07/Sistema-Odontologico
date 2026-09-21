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
    """Cuerpo alternativo para clientes sin cookies.

    Un navegador no lo envía nunca: su token vive en una cookie httpOnly que
    JavaScript no puede leer, y así debe seguir."""

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
