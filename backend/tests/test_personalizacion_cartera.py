"""Asistente de configuración, marca, cartera, gastos fijos y proyección."""

from datetime import date, timedelta


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


LOGO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


async def test_setup_for_a_solo_dentist(client, clinic_with_users):
    h = await _h(client)
    b = (await client.get("/api/v1/clinics/branding", headers=h)).json()
    assert b["setup_completed"] is False

    r = await client.post("/api/v1/clinics/me/setup", headers=h, json={
        "name": "Consultorio Dra. Paz", "practice_type": "independiente", "primary_color": "#7B5BD6",
        "logo_data": LOGO, "slogan": "Sonrisas sanas", "opens_at": "09:00", "closes_at": "17:00",
        "work_days": "12345", "hidden_modules": ["inventory", "laboratory"], "i_am_dentist": True,
        "license_number": "MSP-123", "document_footer": "Gracias por su confianza", "accept_terms": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["terms_version"] == r.json()["terms_current_version"]
    assert r.json()["legal_name"] == "Consultorio Dra. Paz"

    b = (await client.get("/api/v1/clinics/branding", headers=h)).json()
    assert b["setup_completed"] is True and b["primary_color"] == "#7B5BD6"
    assert b["hidden_modules"] == ["inventory", "laboratory"] and b["logo_data"] == LOGO

    profs = (await client.get("/api/v1/professionals", headers=h)).json()
    assert any(p["license_number"] == "MSP-123" for p in profs)

    # Los huecos libres respetan el horario elegido (09:00–17:00, lun–vie).
    prof = next(p for p in profs if p["license_number"] == "MSP-123")
    sab = date.today() + timedelta(days=(5 - date.today().weekday()) % 7 or 7)
    huecos = (await client.get(f"/api/v1/insights/free-slots?professional_id={prof['id']}&date_from={sab}&days=2", headers=h)).json()
    assert huecos == []  # sábado y domingo no se atiende


async def test_branding_validation_and_access(client, clinic_with_users):
    h = await _h(client)
    assert (await client.put("/api/v1/clinics/me", headers=h, json={"primary_color": "rojo"})).status_code == 422
    assert (await client.put("/api/v1/clinics/me", headers=h, json={"logo_data": "data:text/html;base64,AAAA"})).status_code == 422
    assert (await client.put("/api/v1/clinics/me", headers=h, json={"hidden_modules": ["agenda"]})).status_code == 422
    # Cualquier usuario ve la marca; solo el administrador la configura.
    dentist = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    assert (await client.get("/api/v1/clinics/branding", headers=dentist)).status_code == 200
    assert (await client.post("/api/v1/clinics/me/setup", headers=dentist, json={"name": "X1", "practice_type": "clinica"})).status_code == 403


async def test_portfolio_totals_match_accounts(client, clinic_with_users):
    h = await _h(client)
    pid = lambda r: r.json()["id"]
    a = pid(await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Debe"}, headers=h))
    b = pid(await client.post("/api/v1/patients", json={"first_name": "Beto", "last_name": "Pagó"}, headers=h))
    c = pid(await client.post("/api/v1/patients", json={"first_name": "Caro", "last_name": "AFavor"}, headers=h))
    ch = (await client.post(f"/api/v1/patients/{a}/charges", json={"description": "Endodoncia", "amount": "150"}, headers=h)).json()
    await client.post(f"/api/v1/patients/{a}/payments", json={"amount": "50", "method": "efectivo", "charge_id": ch["id"]}, headers=h)
    ch2 = (await client.post(f"/api/v1/patients/{b}/charges", json={"description": "Limpieza", "amount": "30"}, headers=h)).json()
    await client.post(f"/api/v1/patients/{b}/payments", json={"amount": "30", "method": "efectivo", "charge_id": ch2["id"]}, headers=h)
    await client.post(f"/api/v1/patients/{c}/payments", json={"amount": "20", "method": "efectivo"}, headers=h)

    p = (await client.get("/api/v1/finance/portfolio", headers=h)).json()
    por = {r["patient_id"]: r for r in p["patients"]}
    assert por[a]["status"] == "debe" and por[a]["balance"] == "100.00"
    assert por[b]["status"] == "saldado" and por[c]["status"] == "a_favor"
    assert p["summary"]["receivable"] == "100.00" and p["summary"]["credit_balance"] == "20.00"
    fila = next(x for x in p["charges"] if x["charge_id"] == ch["id"])
    assert fila["status"] == "parcial" and fila["pending"] == "100.00"
    # Coincide con el estado de cuenta individual.
    acc = (await client.get(f"/api/v1/patients/{a}/account", headers=h)).json()
    assert acc["balance"] == por[a]["balance"]
    # Solo con permiso de cobros.
    dentist = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    assert (await client.get("/api/v1/finance/portfolio", headers=dentist)).status_code == 403


async def test_recurring_expenses_and_projection(client, clinic_with_users):
    h = await _h(client)
    r = await client.post("/api/v1/finance/recurring-expenses", headers=h, json={
        "description": "Arriendo", "category": "arriendo", "amount": "650", "method": "transferencia", "day_of_month": 5})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["due_this_month"] is True

    proy = (await client.get("/api/v1/finance/projection?days=60", headers=h)).json()
    assert any(i["kind"] == "gasto_fijo" and i["amount"] == "-650.00" for i in proy["items"])

    e = await client.post(f"/api/v1/finance/recurring-expenses/{rec['id']}/register", headers=h, json={})
    assert e.status_code == 201 and e.json()["amount"] == "650.00"
    assert (await client.post(f"/api/v1/finance/recurring-expenses/{rec['id']}/register", headers=h, json={})).status_code == 409
    lista = (await client.get("/api/v1/finance/recurring-expenses", headers=h)).json()
    assert lista[0]["due_this_month"] is False

    # Cuotas de crédito por vencer entran en la proyección.
    pid = (await client.post("/api/v1/patients", json={"first_name": "Lu", "last_name": "Cuotas"}, headers=h)).json()["id"]
    ch = (await client.post(f"/api/v1/patients/{pid}/charges", json={"description": "Ortodoncia", "amount": "300"}, headers=h)).json()
    await client.post(f"/api/v1/patients/{pid}/credits", headers=h, json={
        "charge_id": ch["id"], "installment_count": 3, "frequency": "mensual",
        "first_due_on": (date.today() + timedelta(days=10)).isoformat()})
    proy = (await client.get("/api/v1/finance/projection?days=30", headers=h)).json()
    assert any(i["kind"] == "cuota_credito" and i["amount"] == "100.00" for i in proy["items"])

    assert (await client.delete(f"/api/v1/finance/recurring-expenses/{rec['id']}", headers=h)).status_code == 204
