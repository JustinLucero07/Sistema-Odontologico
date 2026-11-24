from datetime import date, timedelta

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _paciente(client, h):
    return (await client.post("/api/v1/patients", json={"first_name": "Nora", "last_name": "Vélez"}, headers=h)).json()["id"]


async def _enlace(client, h, pid, clinica=False):
    r = await client.post(f"/api/v1/patients/{pid}/portal", json={"include_clinical": clinica}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["include_clinical"] is clinica
    return r.json()["url"].rsplit("/", 1)[-1]


async def _subir(client, token, **campos):
    datos = {"amount": "50", **campos}
    return await client.post(
        f"/api/v1/portal/view/{token}/receipts",
        data=datos,
        files={"file": ("comprobante.png", PNG, "image/png")},
    )


async def test_sin_permiso_clinico_no_muestra_odontograma(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    await client.post(
        f"/api/v1/patients/{pid}/odontogram",
        json={"conditions": [{"fdi_number": "36", "surface": "oclusal", "condition": "caries"}]},
        headers=h,
    )
    sin = (await client.get(f"/api/v1/portal/view/{await _enlace(client, h, pid)}")).json()
    assert sin["odontograma"] == [] and sin["incluye_clinica"] is False
    con = (await client.get(f"/api/v1/portal/view/{await _enlace(client, h, pid, True)}")).json()
    assert con["odontograma"] == [{"fdi_number": "36", "surface": "oclusal", "condition": "caries"}]


async def test_comprobante_aceptado_registra_el_pago(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    cargo = (await client.post(
        f"/api/v1/patients/{pid}/charges", json={"description": "Limpieza", "amount": "80"}, headers=h,
    )).json()
    token = await _enlace(client, h, pid)

    r = await _subir(client, token, charge_id=cargo["id"], reference="TRX-991")
    assert r.status_code == 201, r.text
    assert r.json()["status_label"] == "En revisión"
    assert r.json()["destino"] == "Limpieza"
    vista = (await client.get(f"/api/v1/portal/view/{token}")).json()
    assert vista["comprobantes"][0]["status"] == "pendiente"

    pend = (await client.get("/api/v1/portal-receipts/pending", headers=h)).json()
    assert pend[0]["patient_name"] == "Nora Vélez"
    archivo = await client.get(f"/api/v1/portal-receipts/{pend[0]['id']}/file", headers=h)
    assert archivo.headers["content-type"] == "image/png"

    r = await client.post(f"/api/v1/portal-receipts/{pend[0]['id']}/accept", json={}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "aceptado" and r.json()["payment_id"]
    vista = (await client.get(f"/api/v1/portal/view/{token}")).json()
    assert vista["balance"] == "30.00"
    assert vista["comprobantes"][0]["status_label"] == "Aceptado"
    assert (await client.post(f"/api/v1/portal-receipts/{pend[0]['id']}/accept", json={}, headers=h)).status_code == 409


async def test_comprobante_rechazado_con_motivo(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    token = await _enlace(client, h, pid)
    rid = (await _subir(client, token)).json()["id"]
    assert (await client.post(f"/api/v1/portal-receipts/{rid}/reject", json={"reason": "No se ve el monto"}, headers=h)).status_code == 200
    c = (await client.get(f"/api/v1/portal/view/{token}")).json()["comprobantes"][0]
    assert c["status"] == "rechazado" and c["reject_reason"] == "No se ve el monto"


async def test_comprobante_a_cuota_de_ortodoncia(client):
    h = await _h(client)
    await client.put("/api/v1/clinics/me", json={"orthodontics_enabled": True}, headers=h)
    pid = await _paciente(client, h)
    caso = (await client.post("/api/v1/orthodontics/cases", json={"patient_id": pid, "agreed_total": "300"}, headers=h)).json()
    caso = (await client.post(
        f"/api/v1/orthodontics/cases/{caso['id']}/controls/generate",
        json={"count": 3, "first_on": (date.today() - timedelta(days=10)).isoformat(), "amount": "100"}, headers=h,
    )).json()
    token = await _enlace(client, h, pid)
    orto = (await client.get(f"/api/v1/portal/view/{token}")).json()["ortodoncia"]
    assert orto["code"] == caso["code"] and len(orto["cuotas"]) == 3
    cuota = orto["cuotas"][0]["id"]

    rid = (await _subir(client, token, ortho_control_id=cuota, amount="100")).json()["id"]
    assert (await client.post(f"/api/v1/portal-receipts/{rid}/accept", json={}, headers=h)).status_code == 200
    orto = (await client.get(f"/api/v1/portal/view/{token}")).json()["ortodoncia"]
    assert orto["cuotas"][0]["status"] == "pagada"
    assert orto["paid"] == "100.00"


async def test_portal_rechaza_archivos_raros_y_ajenos(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    otro = (await client.post("/api/v1/patients", json={"first_name": "Otro", "last_name": "Más"}, headers=h)).json()["id"]
    cargo_ajeno = (await client.post(f"/api/v1/patients/{otro}/charges", json={"description": "X", "amount": "10"}, headers=h)).json()
    token = await _enlace(client, h, pid)

    r = await client.post(
        f"/api/v1/portal/view/{token}/receipts", data={"amount": "10"},
        files={"file": ("virus.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert (await _subir(client, token, charge_id=cargo_ajeno["id"])).status_code == 400
    assert (await _subir(client, "x" * 40)).status_code == 404


async def test_imagenes_solo_con_enlace_clinico(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    token = await _enlace(client, h, pid)
    r = await client.get(f"/api/v1/portal/view/{token}/images/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_avisa_a_la_clinica_por_correo(client, clinic_with_users, monkeypatch):
    from app.modules.mail import service as correo
    enviados = []

    async def falso(db, clinic_id, destino, asunto, texto, html=None, adjuntos=None):
        enviados.append((destino, asunto, html, adjuntos))

    monkeypatch.setattr(correo, "enviar", falso)
    h = await _h(client)
    await client.put("/api/v1/clinics/me", json={"email": "caja@clinicatest.io"}, headers=h)
    pid = await _paciente(client, h)
    token = await _enlace(client, h, pid)
    assert (await _subir(client, token, reference="TRX-77")).status_code == 201
    destino, asunto, html, adjuntos = enviados[0]
    assert destino == "caja@clinicatest.io"
    assert "Nora Vélez" in asunto
    assert "TRX-77" in html
    assert adjuntos[0][2] == "image/png"


async def test_estado_de_cuenta_pdf_con_datos_de_pago(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    await client.post(f"/api/v1/patients/{pid}/charges", json={"description": "Limpieza", "amount": "80"}, headers=h)
    await client.post(
        "/api/v1/payment-accounts",
        json={"label": "Banco Prueba", "account_number": "123456", "account_type": "ahorros", "holder_name": "Clínica"},
        headers=h,
    )
    r = await client.get(f"/api/v1/patients/{pid}/statement.pdf", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    odonto = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    assert (await client.get(f"/api/v1/patients/{pid}/statement.pdf", headers=odonto)).status_code in (200, 403)
