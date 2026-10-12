"""Legal y cumplimiento: términos, datos legales y tributarios, solicitudes LOPDP."""

from datetime import date, timedelta


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_setup_requires_accepting_terms(client, clinic_with_users):
    h = await _h(client)
    base = {"name": "Consultorio Uno", "practice_type": "independiente"}
    r = await client.post("/api/v1/clinics/me/setup", headers=h, json=base)
    assert r.status_code == 422 and "Términos" in r.json()["detail"]
    b = (await client.get("/api/v1/clinics/branding", headers=h)).json()
    assert b["setup_completed"] is False and b["terms_pending"] is True

    r = await client.post("/api/v1/clinics/me/setup", headers=h, json={**base, "accept_terms": True})
    assert r.status_code == 200
    assert "admin@clinicatest.io" in r.json()["terms_accepted_by"]
    b = (await client.get("/api/v1/clinics/branding", headers=h)).json()
    assert b["setup_completed"] is True and b["terms_pending"] is False

    # Los textos los sirve el servidor: web y celular ven lo mismo.
    for code in ("terminos", "encargo"):
        d = (await client.get(f"/api/v1/legal/documents/{code}", headers=h)).json()
        assert d["version"] == r.json()["terms_current_version"] and len(d["sections"]) >= 4
    assert (await client.get("/api/v1/legal/documents/otro", headers=h)).status_code == 404


async def test_legal_and_tax_settings(client, clinic_with_users):
    h = await _h(client)
    r = await client.put("/api/v1/clinics/me", headers=h, json={
        "legal_rep_name": "Ana Paz", "legal_rep_id": "1712345678", "dpo_name": "Ana Paz",
        "dpo_email": "datos@consultorio.ec", "health_permit_number": "ACESS-2026-001",
        "health_permit_expires_on": str(date.today() + timedelta(days=200)), "tax_regime": "rimpe_emprendedor",
        "keeps_accounting": False, "sri_establishment": "002", "sri_emission_point": "001", "vat_rate": "0",
        "record_retention_years": 15, "privacy_extra": "Usamos cámaras en recepción.", "session_timeout_minutes": 20,
    })
    assert r.status_code == 200, r.text
    assert r.json()["tax_regime"] == "rimpe_emprendedor" and r.json()["session_timeout_minutes"] == 20
    c = (await client.get("/api/v1/legal/controller", headers=h)).json()
    assert c["dpo_email"] == "datos@consultorio.ec" and c["privacy_extra"].startswith("Usamos")
    b = (await client.get("/api/v1/clinics/branding", headers=h)).json()
    assert b["session_timeout_minutes"] == 20

    for malo in ({"sri_establishment": "1"}, {"tax_regime": "otro"}, {"dpo_email": "sin-arroba"},
                 {"session_timeout_minutes": 5000}):
        assert (await client.put("/api/v1/clinics/me", headers=h, json=malo)).status_code == 422


async def test_rights_requests_crud(client, clinic_with_users):
    h = await _h(client)
    pid = (await client.post("/api/v1/patients", json={"first_name": "Rosa", "last_name": "Vela"}, headers=h)).json()["id"]
    hace20 = str(date.today() - timedelta(days=20))
    r = await client.post("/api/v1/legal/requests", headers=h, json={
        "patient_id": pid, "requester_name": "Rosa Vela", "kind": "acceso", "received_on": hace20,
    })
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["patient_name"] == "Rosa Vela" and s["overdue"] is True and s["kind_label"] == "Acceso"

    s = (await client.put(f"/api/v1/legal/requests/{s['id']}", headers=h, json={
        "patient_id": pid, "requester_name": "Rosa Vela", "kind": "acceso", "received_on": hace20,
        "status": "respondida", "response": "Se entregó copia de sus datos.",
    })).json()
    assert s["resolved_on"] == str(date.today()) and s["overdue"] is False

    lista = (await client.get("/api/v1/legal/requests", headers=h)).json()
    assert len(lista) == 1
    assert (await client.delete(f"/api/v1/legal/requests/{s['id']}", headers=h)).status_code == 204
    assert (await client.get("/api/v1/legal/requests", headers=h)).json() == []

    dentist = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    assert (await client.get("/api/v1/legal/requests", headers=dentist)).status_code == 403
