"""Corregir y anular lo que faltaba: evoluciones, presupuestos y planes."""


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _base(client, h):
    pid = (await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Vela"}, headers=h)).json()["id"]
    tid = (await client.post("/api/v1/treatments", json={"name": "Resina", "default_price": 40}, headers=h)).json()["id"]
    plan = (await client.post(f"/api/v1/patients/{pid}/treatment-plans", headers=h, json={
        "title": "Plan", "items": [{"treatment_id": tid, "fdi_number": "16", "price": 40}, {"treatment_id": tid, "fdi_number": "26", "price": 40}],
    })).json()
    return pid, tid, plan


async def test_void_evolution(client, clinic_with_users):
    h = await _h(client)
    pid, _, _ = await _base(client, h)
    ev = (await client.post(f"/api/v1/patients/{pid}/evolutions", json={"procedure": "Resina 16"}, headers=h)).json()
    assert (await client.post(f"/api/v1/evolutions/{ev['id']}/void", json={"reason": "x"}, headers=h)).status_code == 422
    r = await client.post(f"/api/v1/evolutions/{ev['id']}/void", json={"reason": "Paciente equivocado"}, headers=h)
    assert r.status_code == 200 and r.json()["voided_at"] and r.json()["procedure"] == "Resina 16"
    # Anulada: ni se edita ni se anula otra vez.
    assert (await client.put(f"/api/v1/evolutions/{ev['id']}", json={"procedure": "X"}, headers=h)).status_code == 409
    assert (await client.post(f"/api/v1/evolutions/{ev['id']}/void", json={"reason": "otra vez"}, headers=h)).status_code == 409
    lista = (await client.get(f"/api/v1/patients/{pid}/evolutions", headers=h)).json()
    assert lista[0]["void_reason"] == "Paciente equivocado"


async def test_edit_and_void_budget(client, clinic_with_users):
    h = await _h(client)
    pid, _, plan = await _base(client, h)
    b = (await client.post(f"/api/v1/patients/{pid}/budgets", json={"treatment_plan_id": plan["id"]}, headers=h)).json()
    assert b["total"] == 80
    r = await client.put(f"/api/v1/budgets/{b['id']}", headers=h, json={
        "notes": "Con descuento", "items": [{"description": "Resina 16", "price": 40, "discount": 10}],
    })
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 30 and len(r.json()["items"]) == 1 and r.json()["notes"] == "Con descuento"
    r = await client.post(f"/api/v1/budgets/{b['id']}/void", json={"reason": "Se rehízo"}, headers=h)
    assert r.json()["status"] == "anulado" and r.json()["void_reason"] == "Se rehízo"
    assert (await client.put(f"/api/v1/budgets/{b['id']}", json={"notes": "x"}, headers=h)).status_code == 409
    assert (await client.put(f"/api/v1/budgets/{b['id']}/status", json={"status": "aceptado"}, headers=h)).status_code == 409


async def test_accepted_budget_needs_charge_voided_first(client, clinic_with_users):
    h = await _h(client)
    pid, _, plan = await _base(client, h)
    b = (await client.post(f"/api/v1/patients/{pid}/budgets", json={"treatment_plan_id": plan["id"]}, headers=h)).json()
    await client.put(f"/api/v1/budgets/{b['id']}/status", json={"status": "aceptado"}, headers=h)
    assert (await client.put(f"/api/v1/budgets/{b['id']}", json={"notes": "x"}, headers=h)).status_code == 409
    r = await client.post(f"/api/v1/budgets/{b['id']}/void", json={"reason": "Error"}, headers=h)
    assert r.status_code == 409 and "cargo" in r.json()["detail"]
    cargo = next(c for c in (await client.get(f"/api/v1/patients/{pid}/account", headers=h)).json()["charges"] if c.get("voided_at") is None)
    await client.post(f"/api/v1/finance/charges/{cargo['id']}/void", json={"reason": "Presupuesto mal hecho"}, headers=h)
    assert (await client.post(f"/api/v1/budgets/{b['id']}/void", json={"reason": "Error"}, headers=h)).status_code == 200


async def test_cancel_whole_plan(client, clinic_with_users):
    h = await _h(client)
    pid, tid, plan = await _base(client, h)
    hecho = plan["items"][0]["id"]
    await client.put(f"/api/v1/treatment-plans/{plan['id']}/items/{hecho}", json={"status": "completado"}, headers=h)
    r = await client.post(f"/api/v1/treatment-plans/{plan['id']}/cancel", json={"reason": "El paciente se mudó"}, headers=h)
    assert r.status_code == 200, r.text
    estados = {i["id"]: i["status"] for i in r.json()["items"]}
    assert estados[hecho] == "completado" and list(estados.values()).count("cancelado") == 1
    assert r.json()["cancel_reason"] == "El paciente se mudó"
    assert (await client.post(f"/api/v1/treatment-plans/{plan['id']}/items", json={"treatment_id": tid}, headers=h)).status_code == 409
