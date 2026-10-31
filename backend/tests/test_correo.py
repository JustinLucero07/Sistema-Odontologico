"""Correo saliente de cada consulta, contra un servidor SMTP real (aiosmtpd)
que corre durante la prueba."""

from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy

import pytest
from aiosmtpd.controller import Controller
from sqlalchemy import select, update

from app.modules.appointments.models import AppointmentReminder
from app.modules.mail.models import MailSettings
from tests.sri_falso import SriFalso, preparar_emisor


class _Buzon:
    def __init__(self):
        self.correos = []

    async def handle_DATA(self, server, session, envelope):
        self.correos.append(message_from_bytes(envelope.content, policy=policy.default))
        return "250 OK"


@pytest.fixture
def smtp():
    import socket

    with socket.socket() as libre:
        libre.bind(("127.0.0.1", 0))
        puerto = libre.getsockname()[1]
    buzon = _Buzon()
    ctl = Controller(buzon, hostname="127.0.0.1", port=puerto)
    ctl.start()
    buzon.port = puerto
    yield buzon
    ctl.stop()


async def _login(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _configurar(client, h, puerto):
    r = await client.put("/api/v1/mail/settings", headers=h, json={
        "host": "127.0.0.1", "port": puerto, "security": "none", "username": None,
        "password": "secreta-de-prueba", "from_email": "citas@clinicatest.io", "from_name": "Clínica Test",
    })
    assert r.status_code == 200, r.text
    return r.json()


async def test_sin_configurar(client, clinic_with_users):
    h = await _login(client)
    r = await client.get("/api/v1/mail/settings", headers=h)
    assert r.status_code == 200 and r.json()["configured"] is False and r.json()["source"] == "ninguno"
    r = await client.post("/api/v1/mail/test", headers=h, json={"to": "x@y.com"})
    assert r.json()["last_test_ok"] is False and "no está configurado" in r.json()["last_error"]


async def test_prueba_llega_y_la_clave_queda_cifrada(client, clinic_with_users, db_session, smtp):
    h = await _login(client)
    datos = await _configurar(client, h, smtp.port)
    assert datos["configured"] and datos["source"] == "consulta" and datos["has_password"]
    assert "secreta" not in str(datos)

    guardada = (await db_session.execute(select(MailSettings.password))).scalar_one()
    assert b"secreta-de-prueba" not in guardada

    r = await client.post("/api/v1/mail/test", headers=h, json={"to": "doctora@correo.ec"})
    assert r.json()["last_test_ok"] is True, r.json()["last_error"]
    assert len(smtp.correos) == 1
    m = smtp.correos[0]
    assert m["To"] == "doctora@correo.ec" and "citas@clinicatest.io" in m["From"]
    assert "Prueba de correo" in m["Subject"]
    assert m.get_body(preferencelist=("html",)) is not None


async def test_servidor_inalcanzable_explica_el_error(client, clinic_with_users):
    h = await _login(client)
    await _configurar(client, h, 1)  # nadie escucha en el puerto 1
    r = await client.post("/api/v1/mail/test", headers=h, json={"to": "x@y.com"})
    assert r.json()["last_test_ok"] is False
    assert "No se pudo conectar" in r.json()["last_error"]


async def test_recordatorio_de_cita_sale_por_correo(client, clinic_with_users, db_session, smtp):
    h = await _login(client)
    await _configurar(client, h, smtp.port)
    pid = (await client.post("/api/v1/patients", headers=h, json={
        "first_name": "Lucía", "last_name": "Arce", "email": "lucia@correo.ec", "whatsapp": "0999123456"})).json()["id"]
    prof = (await client.post("/api/v1/professionals", headers=h, json={"first_name": "Ana", "last_name": "Paz"})).json()["id"]
    inicio = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=15, minute=0, second=0, microsecond=0)
    # Sin indicar canales (como la app móvil): WhatsApp y correo.
    r = await client.post("/api/v1/appointments", headers=h, json={
        "patient_id": pid, "professional_id": prof,
        "starts_at": inicio.isoformat(), "ends_at": (inicio + timedelta(minutes=30)).isoformat()})
    assert r.status_code == 201, r.text
    canales = {c for (c,) in (await db_session.execute(select(AppointmentReminder.channel))).all()}
    assert canales == {"whatsapp", "email"}

    # Llega el momento del recordatorio por correo.
    await db_session.execute(
        update(AppointmentReminder).where(AppointmentReminder.channel == "email")
        .values(scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    await db_session.commit()
    r = await client.post("/api/v1/messaging/dispatch", headers=h)
    assert r.status_code == 200 and r.json()["sent"] >= 1, r.text
    assert any(m["To"] == "lucia@correo.ec" and "Recordatorio" in m["Subject"] for m in smtp.correos)
    mensajes = (await client.get(f"/api/v1/messaging/messages?patient_id={pid}", headers=h)).json()
    assert any(m["channel"] == "email" and m["status"] == "enviado" for m in mensajes)


async def test_factura_llega_con_pdf_y_xml(client, clinic_with_users, monkeypatch, smtp):
    SriFalso(monkeypatch)
    h = await _login(client)
    await preparar_emisor(client, h)
    await _configurar(client, h, smtp.port)
    pid = (await client.post("/api/v1/patients", headers=h, json={
        "first_name": "María", "last_name": "Gómez", "national_id": "1710034065", "email": "maria@correo.ec"})).json()["id"]
    f = (await client.post("/api/v1/invoices", headers=h, json={
        "patient_id": pid, "items": [{"description": "Consulta", "unit_price": "25"}]})).json()
    assert f["status"] == "autorizada" and f["emailed_at"], f
    m = next(m for m in smtp.correos if m["To"] == "maria@correo.ec")
    nombres = {a.get_filename() for a in m.iter_attachments()}
    assert nombres == {f"factura-{f['number']}.pdf", f"factura-{f['number']}.xml"}
