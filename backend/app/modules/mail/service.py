import asyncio
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_settings
from app.modules.clinics.models import Clinic
from app.modules.invoicing import crypto
from app.modules.mail.models import MailSettings
from app.modules.mail.schemas import MailSettingsOut, MailSettingsUpdate


class CorreoNoConfigurado(Exception):
    pass


class CorreoFallido(Exception):
    pass


@dataclass
class Servidor:
    host: str
    port: int
    security: str
    username: str | None
    password: str | None
    from_email: str
    from_name: str | None


async def _fila(db: AsyncSession, clinic_id: uuid.UUID) -> MailSettings:
    fila = (await db.execute(select(MailSettings).where(MailSettings.clinic_id == clinic_id))).scalar_one_or_none()
    if fila is None:
        fila = MailSettings(clinic_id=clinic_id, port=587, security="starttls", reminders_enabled=True)
        db.add(fila)
        await db.flush()
    return fila


def _del_servidor() -> Servidor | None:
    """Respaldo: el SMTP de las variables de entorno del servidor."""
    s = get_settings()
    if not (s.SMTP_HOST and s.SMTP_FROM):
        return None
    return Servidor(
        host=s.SMTP_HOST, port=s.SMTP_PORT, security="ssl" if s.SMTP_PORT == 465 else "starttls",
        username=s.SMTP_USER, password=s.SMTP_PASSWORD, from_email=s.SMTP_FROM, from_name=None,
    )


async def servidor(db: AsyncSession, clinic_id: uuid.UUID) -> tuple[Servidor | None, str]:
    """El buzón que se usará y de dónde sale: el de la consulta primero."""
    fila = await _fila(db, clinic_id)
    if fila.host and fila.from_email:
        clave = crypto.descifrar(fila.password).decode() if fila.password else None
        return (
            Servidor(fila.host, fila.port, fila.security, fila.username, clave, fila.from_email, fila.from_name),
            "consulta",
        )
    respaldo = _del_servidor()
    return (respaldo, "servidor") if respaldo else (None, "ninguno")


async def configurado(db: AsyncSession, clinic_id: uuid.UUID) -> bool:
    return (await servidor(db, clinic_id))[0] is not None


async def recordatorios_activos(db: AsyncSession, clinic_id: uuid.UUID) -> bool:
    return (await _fila(db, clinic_id)).reminders_enabled and await configurado(db, clinic_id)


async def get_settings_out(db: AsyncSession, clinic_id: uuid.UUID) -> MailSettingsOut:
    fila = await _fila(db, clinic_id)
    srv, fuente = await servidor(db, clinic_id)
    return MailSettingsOut(
        configured=srv is not None,
        source=fuente,
        host=fila.host,
        port=fila.port,
        security=fila.security,
        username=fila.username,
        has_password=fila.password is not None,
        from_email=fila.from_email,
        from_name=fila.from_name,
        reminders_enabled=fila.reminders_enabled,
        last_test_at=fila.last_test_at,
        last_test_ok=fila.last_test_ok,
        last_error=fila.last_error,
    )


async def update_settings(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, datos: MailSettingsUpdate) -> MailSettingsOut:
    fila = await _fila(db, clinic_id)
    cambios = datos.model_dump(exclude_unset=True)
    for campo in ("host", "username", "from_name"):
        if campo in cambios:
            setattr(fila, campo, (cambios[campo] or "").strip() or None)
    if "from_email" in cambios:
        fila.from_email = str(cambios["from_email"]) if cambios["from_email"] else None
    if cambios.get("port"):
        fila.port = cambios["port"]
    if cambios.get("security"):
        fila.security = cambios["security"]
    if cambios.get("reminders_enabled") is not None:
        fila.reminders_enabled = cambios["reminders_enabled"]
    if cambios.get("password"):
        fila.password = crypto.cifrar(cambios["password"].encode())
    # Cambió el buzón: la última prueba ya no dice nada.
    if {"host", "port", "security", "username", "password", "from_email"} & cambios.keys():
        fila.last_test_at = fila.last_test_ok = fila.last_error = None
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="mail_settings",
        entity_id=str(fila.id), after={k: ("***" if k == "password" else v) for k, v in cambios.items()},
    )
    return await get_settings_out(db, clinic_id)


async def clear_settings(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID) -> MailSettingsOut:
    fila = await _fila(db, clinic_id)
    fila.host = fila.username = fila.password = fila.from_email = fila.from_name = None
    fila.last_test_at = fila.last_test_ok = fila.last_error = None
    await db.flush()
    await record_audit(db, clinic_id=clinic_id, user_id=actor_id, action="clear", entity_type="mail_settings", entity_id=str(fila.id))
    return await get_settings_out(db, clinic_id)


def _mensaje_amable(e: Exception) -> str:
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return (
            "El servidor rechazó el usuario o la contraseña. En Gmail y Outlook hay que usar una "
            "«contraseña de aplicación», no la contraseña normal de la cuenta."
        )
    if isinstance(e, (smtplib.SMTPConnectError, ConnectionRefusedError, TimeoutError, OSError)) and not isinstance(e, smtplib.SMTPException):
        return f"No se pudo conectar con el servidor de correo ({e}). Revise el servidor y el puerto."
    if isinstance(e, smtplib.SMTPRecipientsRefused):
        return "El servidor rechazó la dirección de destino."
    if isinstance(e, smtplib.SMTPSenderRefused):
        return "El servidor no permite enviar con ese remitente: use la misma dirección de la cuenta."
    return f"El correo no se pudo enviar: {e}"


def _enviar_sync(srv: Servidor, destino: str, asunto: str, texto: str, html: str | None, adjuntos: list[tuple[str, bytes, str]]) -> None:
    msj = EmailMessage()
    msj["From"] = formataddr((srv.from_name or "", srv.from_email))
    msj["To"] = destino
    msj["Subject"] = asunto
    msj["Message-ID"] = make_msgid(domain=srv.from_email.split("@")[-1])
    msj.set_content(texto)
    if html:
        msj.add_alternative(html, subtype="html")
    for nombre, datos, tipo in adjuntos:
        principal, secundario = tipo.split("/", 1)
        msj.add_attachment(datos, maintype=principal, subtype=secundario, filename=nombre)
    contexto = ssl.create_default_context()
    if srv.security == "ssl":
        smtp = smtplib.SMTP_SSL(srv.host, srv.port, context=contexto, timeout=30)
    else:
        smtp = smtplib.SMTP(srv.host, srv.port, timeout=30)
    with smtp:
        if srv.security == "starttls":
            smtp.starttls(context=contexto)
        if srv.username:
            smtp.login(srv.username, srv.password or "")
        smtp.send_message(msj)


async def enviar(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    destino: str,
    asunto: str,
    texto: str,
    html: str | None = None,
    adjuntos: list[tuple[str, bytes, str]] | None = None,
) -> None:
    srv, _ = await servidor(db, clinic_id)
    if srv is None:
        raise CorreoNoConfigurado("El correo saliente no está configurado. Configúrelo en Configuración → Correo.")
    try:
        await asyncio.to_thread(_enviar_sync, srv, destino, asunto, texto, html, adjuntos or [])
    except Exception as e:  # cualquier fallo de red o del servidor, en palabras claras
        raise CorreoFallido(_mensaje_amable(e)) from e


async def probar(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, destino: str) -> MailSettingsOut:
    fila = await _fila(db, clinic_id)
    clinica = (await db.execute(select(Clinic).where(Clinic.id == clinic_id))).scalar_one()
    fila.last_test_at = datetime.now(timezone.utc)
    try:
        await enviar(
            db, clinic_id, destino, f"Prueba de correo — {clinica.name}",
            f"Este es un correo de prueba de {clinica.name}.\n\nSi lo recibe, las facturas y los "
            "recordatorios de citas ya pueden salir por correo.",
            pagina(clinica, "Correo de prueba", [
                f"Este es un correo de prueba de <b>{escapar(clinica.name)}</b>.",
                "Si lo recibe, las facturas y los recordatorios de citas ya pueden salir por correo.",
            ]),
        )
        fila.last_test_ok, fila.last_error = True, None
    except (CorreoNoConfigurado, CorreoFallido) as e:
        fila.last_test_ok, fila.last_error = False, str(e)[:500]
    await db.flush()
    await record_audit(db, clinic_id=clinic_id, user_id=actor_id, action="test", entity_type="mail_settings", entity_id=str(fila.id), after={"ok": fila.last_test_ok})
    return await get_settings_out(db, clinic_id)


def escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def pagina(clinica: Clinic, titulo: str, parrafos: list[str], boton: tuple[str, str] | None = None) -> str:
    """Correo HTML sencillo con el color de la consulta. Los párrafos ya vienen
    escapados (pueden traer <b>)."""
    color = clinica.primary_color or "#0D7F76"
    cuerpo = "".join(f'<p style="margin:0 0 14px;line-height:1.55">{p}</p>' for p in parrafos)
    accion = (
        f'<p style="margin:22px 0"><a href="{escapar(boton[1])}" style="background:{color};color:#fff;'
        f'padding:12px 22px;border-radius:12px;text-decoration:none;font-weight:600">{escapar(boton[0])}</a></p>'
        if boton else ""
    )
    pie = escapar(" · ".join(x for x in [clinica.name, clinica.address or "", clinica.phone or ""] if x))
    return (
        '<!doctype html><html><body style="margin:0;background:#f6f4ef;font-family:Arial,Helvetica,sans-serif;color:#14242b">'
        '<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:28px 12px">'
        '<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#fff;border-radius:18px;overflow:hidden">'
        f'<tr><td style="background:{color};padding:20px 28px;color:#fff;font-size:18px;font-weight:700">{escapar(clinica.name)}</td></tr>'
        f'<tr><td style="padding:28px"><h1 style="margin:0 0 16px;font-size:22px">{escapar(titulo)}</h1>{cuerpo}{accion}</td></tr>'
        f'<tr><td style="padding:16px 28px;background:#faf9f6;color:#6b7a7e;font-size:12px">{pie}</td></tr>'
        "</table></td></tr></table></body></html>"
    )
