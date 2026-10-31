from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.mail import service
from app.modules.mail.schemas import MailSettingsOut, MailSettingsUpdate, MailTest

router = APIRouter(prefix="/api/v1/mail", tags=["mail"])

# Atajos para los proveedores más comunes: así nadie tiene que buscar
# servidores y puertos.
PROVEEDORES = [
    {"code": "gmail", "label": "Gmail / Google Workspace", "host": "smtp.gmail.com", "port": 587, "security": "starttls",
     "help": "Active la verificación en dos pasos y cree una «contraseña de aplicación» en myaccount.google.com → Seguridad."},
    {"code": "outlook", "label": "Outlook / Microsoft 365", "host": "smtp.office365.com", "port": 587, "security": "starttls",
     "help": "Use la cuenta completa como usuario. Si tiene verificación en dos pasos, cree una contraseña de aplicación."},
    {"code": "zoho", "label": "Zoho Mail", "host": "smtp.zoho.com", "port": 465, "security": "ssl",
     "help": "Use la contraseña de aplicación de Zoho."},
    {"code": "yahoo", "label": "Yahoo", "host": "smtp.mail.yahoo.com", "port": 465, "security": "ssl",
     "help": "Genere una contraseña de aplicación en la seguridad de su cuenta."},
    {"code": "otro", "label": "Otro (el de su dominio o hosting)", "host": "", "port": 587, "security": "starttls",
     "help": "Su proveedor de hosting le indica el servidor SMTP, el puerto y el usuario."},
]


@router.get("/providers")
async def get_providers(current_user: CurrentUser = Depends(require_permission("settings:manage"))):
    return PROVEEDORES


@router.get("/settings", response_model=MailSettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.get_settings_out(db, current_user.clinic_id)
    await db.commit()
    return out


@router.put("/settings", response_model=MailSettingsOut)
async def put_settings(
    payload: MailSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.update_settings(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return out


@router.delete("/settings", response_model=MailSettingsOut)
async def delete_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.clear_settings(db, current_user.clinic_id, current_user.id)
    await db.commit()
    return out


@router.post("/test", response_model=MailSettingsOut)
async def post_test(
    payload: MailTest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    out = await service.probar(db, current_user.clinic_id, current_user.id, str(payload.to))
    await db.commit()
    return out
