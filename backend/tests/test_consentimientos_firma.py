"""Consentimientos completos: biblioteca, datos del paciente en el texto,
firma dibujada, firma a distancia por enlace, correo y PDF."""

import base64
import hashlib

from app.modules.consents.library import BIBLIOTECA
from tests.test_correo import _configurar, smtp  # noqa: F401  (fixture)
from tests.test_phase7 import _png_bytes

FIRMA = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()


async def _login(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _base(client, h):
    pid = (await client.post("/api/v1/patients", headers=h, json={
        "first_name": "Lucía", "last_name": "Arce", "national_id": "1710034065", "birth_date": "1990-05-04",
        "email": "lucia@correo.ec", "city": "Quito"})).json()["id"]
    prof = (await client.post("/api/v1/professionals", headers=h, json={
        "first_name": "Ana", "last_name": "Paz", "license_number": "MSP-12345"})).json()["id"]
    r = await client.post("/api/v1/consents/library", headers=h, json={})
    assert r.status_code == 200 and r.json()["added"] == len(BIBLIOTECA)
    plantillas = (await client.get("/api/v1/consents/templates", headers=h)).json()
    endo = next(t for t in plantillas if t["procedure_type"] == "endodoncia")
    r = await client.post(f"/api/v1/patients/{pid}/consents", headers=h, json={
        "template_id": endo["id"], "professional_id": prof, "tooth": "36", "notes": "Paciente con molestia previa"})
    assert r.status_code == 201, r.text
    return pid, r.json()


async def test_biblioteca_y_datos_rellenados(client, clinic_with_users):
    h = await _login(client)
    lib = (await client.get("/api/v1/consents/library", headers=h)).json()
    assert len(lib) == len(BIBLIOTECA) >= 12 and not any(x["added"] for x in lib)
    _, c = await _base(client, h)
    assert all(x["added"] for x in (await client.get("/api/v1/consents/library", headers=h)).json())
    # Agregar otra vez no duplica.
    assert (await client.post("/api/v1/consents/library", headers=h, json={})).json()["added"] == 0

    cuerpo = c["body"]
    for esperado in ("Lucía Arce", "1710034065", "Ana Paz", "MSP-12345", "pieza 36", "Quito", "Paciente con molestia previa"):
        assert esperado in cuerpo, esperado
    assert "{" not in cuerpo
    assert c["content_hash"] == hashlib.sha256(f"{c['title']}\n\n{cuerpo}".encode()).hexdigest()


async def test_firma_presencial_dibujada(client, clinic_with_users):
    h = await _login(client)
    _, c = await _base(client, h)
    mala = await client.put(f"/api/v1/consents/{c['id']}/sign", headers=h, json={
        "signed_by_name": "Lucía Arce", "signature_image": "data:image/png;base64,bm8gZXMgdW4gcG5n"})
    assert mala.status_code == 422
    r = await client.put(f"/api/v1/consents/{c['id']}/sign", headers=h, json={
        "signed_by_name": "Lucía Arce", "signer_id_number": "1710034065", "signer_relationship": "paciente",
        "signature_image": FIRMA, "professional_signature_image": FIRMA, "witness_name": "Rosa Vera"})
    assert r.status_code == 200, r.text
    f = r.json()
    assert f["status"] == "firmado" and f["signed_channel"] == "presencial" and f["signature_image"] == FIRMA
    pdf = await client.get(f"/api/v1/consents/{c['id']}/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


async def test_firma_a_distancia_un_solo_uso(client, clinic_with_users):
    h = await _login(client)
    pid, c = await _base(client, h)
    r = await client.post(f"/api/v1/consents/{c['id']}/sign-link", headers=h, json={})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert "/firmar/" in url and r.json()["emailed"] is False
    token = url.rsplit("/", 1)[1]

    # Sin sesión: el enlace es la credencial.
    vista = await client.get(f"/api/v1/public/consents/{token}")
    assert vista.status_code == 200
    assert vista.json()["patient_name"] == "Lucía Arce" and "pieza 36" in vista.json()["body"]

    sin_aceptar = await client.post(f"/api/v1/public/consents/{token}/sign", json={
        "signed_by_name": "Lucía Arce", "signature_image": FIRMA, "accept": False})
    assert sin_aceptar.status_code == 422
    sin_firma = await client.post(f"/api/v1/public/consents/{token}/sign", json={
        "signed_by_name": "Lucía Arce", "signature_image": "", "accept": True})
    assert sin_firma.status_code == 422
    ok = await client.post(f"/api/v1/public/consents/{token}/sign", json={
        "signed_by_name": "Lucía Arce", "signer_id_number": "1710034065", "signature_image": FIRMA, "accept": True},
        headers={"User-Agent": "Telefono de prueba"})
    assert ok.status_code == 200, ok.text

    # Ya no sirve: un solo uso.
    assert (await client.get(f"/api/v1/public/consents/{token}")).status_code == 404
    firmado = next(x for x in (await client.get(f"/api/v1/patients/{pid}/consents", headers=h)).json() if x["id"] == c["id"])
    assert firmado["status"] == "firmado" and firmado["signed_channel"] == "remoto" and firmado["signed_ip"]


async def test_enlace_anulado_o_invalido(client, clinic_with_users):
    h = await _login(client)
    _, c = await _base(client, h)
    token = (await client.post(f"/api/v1/consents/{c['id']}/sign-link", headers=h, json={})).json()["url"].rsplit("/", 1)[1]
    await client.post(f"/api/v1/consents/{c['id']}/void", headers=h, json={"reason": "Emitido por error"})
    assert (await client.get(f"/api/v1/public/consents/{token}")).status_code == 404
    assert (await client.get("/api/v1/public/consents/" + "x" * 43)).status_code == 404


async def test_enlace_por_correo(client, clinic_with_users, smtp):  # noqa: F811
    h = await _login(client)
    await _configurar(client, h, smtp.port)
    _, c = await _base(client, h)
    r = await client.post(f"/api/v1/consents/{c['id']}/sign-link", headers=h, json={"send_email": True})
    assert r.json()["emailed"] is True, r.json()
    m = next(m for m in smtp.correos if m["To"] == "lucia@correo.ec")
    assert "Consentimiento para firmar" in m["Subject"]
    assert r.json()["url"] in m.get_body(preferencelist=("plain",)).get_content()
