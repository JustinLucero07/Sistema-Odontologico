import uuid

from pydantic import BaseModel, EmailStr, Field


class PermissionOut(BaseModel):
    id: uuid.UUID
    code: str
    module: str
    description: str

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_codes: list[str] | None = None


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionOut]

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role_ids: list[uuid.UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    role_ids: list[uuid.UUID] | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_superadmin: bool
    roles: list[RoleOut]

    model_config = {"from_attributes": True}
