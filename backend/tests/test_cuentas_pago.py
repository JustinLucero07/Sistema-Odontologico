import base64

QR = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\nqr").decode()


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_crud_y_visibilidad(client):
    admin = await _h(client)
    odonto = await _h(client, "dentist@clinicatest.io", "Dentist123!")

    # Sin QR ni datos de cuenta no tiene sentido.
    r = await client.post("/api/v1/payment-accounts", json={"label": "Banco Pichincha"}, headers=admin)
    assert r.status_code == 422
    r = await client.post("/api/v1/payment-accounts", json={"label": "X", "qr_data": "data:text/html;base64,AAA"}, headers=admin)
    assert r.status_code == 422

    r = await client.post(
        "/api/v1/payment-accounts",
        json={"label": "Banco Pichincha", "qr_data": QR, "holder_name": "Clínica Sonrisa", "account_type": "ahorros",
              "account_number": "2201234567", "holder_id": "1790011223001", "note": "Envíe el comprobante por WhatsApp"},
        headers=admin,
    )
    assert r.status_code == 201, r.text
    pichincha = r.json()
    r = await client.post("/api/v1/payment-accounts", json={"label": "DeUna", "qr_data": QR}, headers=admin)
    deuna = r.json()
    assert deuna["sort_order"] > pichincha["sort_order"]

    # El odontólogo las ve pero no las cambia.
    assert len((await client.get("/api/v1/payment-accounts", headers=odonto)).json()) == 2
    r = await client.put(f"/api/v1/payment-accounts/{deuna['id']}", json={"label": "Otro"}, headers=odonto)
    assert r.status_code == 403

    r = await client.put(f"/api/v1/payment-accounts/{deuna['id']}", json={"is_active": False}, headers=admin)
    assert r.json()["is_active"] is False
    assert [a["label"] for a in (await client.get("/api/v1/payment-accounts", headers=odonto)).json()] == ["Banco Pichincha"]
    assert len((await client.get("/api/v1/payment-accounts?all=true", headers=admin)).json()) == 2

    # Quitar el QR de una cuenta sin datos de transferencia no se permite.
    r = await client.put(f"/api/v1/payment-accounts/{deuna['id']}", json={"qr_data": None}, headers=admin)
    assert r.status_code == 422

    # Reordenar.
    r = await client.post("/api/v1/payment-accounts/reorder", json={"ids": [deuna["id"], pichincha["id"]]}, headers=admin)
    assert [a["label"] for a in r.json()] == ["DeUna", "Banco Pichincha"]

    # Eliminar.
    assert (await client.delete(f"/api/v1/payment-accounts/{deuna['id']}", headers=admin)).status_code == 204
    assert len((await client.get("/api/v1/payment-accounts?all=true", headers=admin)).json()) == 1


async def test_el_paciente_las_ve_en_su_portal(client):
    admin = await _h(client)
    await client.post(
        "/api/v1/payment-accounts",
        json={"label": "Banco Guayaquil", "account_number": "0012345678", "account_type": "corriente"},
        headers=admin,
    )
    pid = (await client.post("/api/v1/patients", json={"first_name": "Lucía", "last_name": "Arce"}, headers=admin)).json()["id"]
    enlace = (await client.post(f"/api/v1/patients/{pid}/portal", json={}, headers=admin)).json()["url"]
    token = enlace.rstrip("/").split("/")[-1]
    vista = (await client.get(f"/api/v1/portal/view/{token}")).json()
    assert vista["payment_accounts"][0]["label"] == "Banco Guayaquil"
    assert vista["payment_accounts"][0]["account_number"] == "0012345678"
