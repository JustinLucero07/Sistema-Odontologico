from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.rate_limit import limiter
from app.modules.auth import service
from app.modules.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


# Una app móvil no tiene almacén de cookies y guarda el token en el llavero
# del sistema. Lo pide con esta cabecera; un navegador nunca la envía, así que
# su token sigue viviendo solo en una cookie httpOnly fuera del alcance de
# JavaScript — que es la razón de que esté ahí.
TOKEN_IN_BODY_HEADER = "x-token-delivery"


def _wants_token_in_body(request: Request) -> bool:
    return request.headers.get(TOKEN_IN_BODY_HEADER, "").lower() == "body"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=AccessTokenResponse)
@limiter.limit("10/minute")
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    user = await service.authenticate(db, payload.email, payload.password, ip_address)
    access_token = service.build_access_token(user)
    raw_refresh_token = await service.issue_refresh_token(db, user, request.headers.get("user-agent"), ip_address)
    await db.commit()

    _set_refresh_cookie(response, raw_refresh_token)
    return AccessTokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token if _wants_token_in_body(request) else None,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    # La cookie manda cuando existe: un navegador no debe poder sortearla
    # mandando un token en el cuerpo.
    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not raw_token and payload is not None:
        raw_token = payload.refresh_token
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No hay sesión activa")

    ip_address = request.client.host if request.client else None
    user, new_raw_token = await service.rotate_refresh_token(
        db, raw_token, request.headers.get("user-agent"), ip_address
    )
    access_token = service.build_access_token(user)
    await db.commit()

    _set_refresh_cookie(response, new_raw_token)
    return AccessTokenResponse(
        access_token=access_token,
        refresh_token=new_raw_token if _wants_token_in_body(request) else None,
    )


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not raw_token and payload is not None:
        raw_token = payload.refresh_token
    if raw_token:
        await service.revoke_refresh_token(db, raw_token)
        await db.commit()
    response.delete_cookie(key=settings.REFRESH_TOKEN_COOKIE_NAME, path="/api/v1/auth")


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser = Depends(get_current_user)):
    user = current_user.user
    return MeResponse(
        id=user.id,
        clinic_id=user.clinic_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superadmin=user.is_superadmin,
        roles=[role.name for role in user.roles],
        permissions=sorted(current_user.permissions),
    )
