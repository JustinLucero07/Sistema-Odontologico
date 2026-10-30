"""Envío por correo del comprobante (PDF + XML autorizado) al paciente.

Usa el servidor SMTP de SMTP_HOST. Sin configurar, no se envía nada: la
factura sigue disponible para descargarla o mandarla por WhatsApp."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import get_settings


def configurado() -> bool:
    s = get_settings()
    return bool(s.SMTP_HOST and s.SMTP_FROM)


def _enviar(destino: str, asunto: str, texto: str, adjuntos: list[tuple[str, bytes, str]]) -> None:
    s = get_settings()
    msj = EmailMessage()
    msj["From"] = s.SMTP_FROM
    msj["To"] = destino
    msj["Subject"] = asunto
    msj.set_content(texto)
    for nombre, datos, tipo in adjuntos:
        principal, secundario = tipo.split("/", 1)
        msj.add_attachment(datos, maintype=principal, subtype=secundario, filename=nombre)
    contexto = ssl.create_default_context()
    if s.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(s.SMTP_HOST, s.SMTP_PORT, context=contexto, timeout=30) as smtp:
            if s.SMTP_USER:
                smtp.login(s.SMTP_USER, s.SMTP_PASSWORD or "")
            smtp.send_message(msj)
    else:
        with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=30) as smtp:
            smtp.starttls(context=contexto)
            if s.SMTP_USER:
                smtp.login(s.SMTP_USER, s.SMTP_PASSWORD or "")
            smtp.send_message(msj)


async def enviar(destino: str, asunto: str, texto: str, adjuntos: list[tuple[str, bytes, str]]) -> None:
    await asyncio.to_thread(_enviar, destino, asunto, texto, adjuntos)
