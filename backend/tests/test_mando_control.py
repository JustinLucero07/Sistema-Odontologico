from datetime import date


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_meta_avance_y_cobrado_hoy(client):
    admin = await _h(client)
    pid = (await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Mora"}, headers=admin)).json()["id"]
    await client.post(f"/api/v1/patients/{pid}/payments", json={"amount": "250", "method": "efectivo"}, headers=admin)

    c = (await client.get("/api/v1/dashboard/control", headers=admin)).json()
    assert c["collected_today"] == "250.00"
    assert c["payments_today"] == 1
    assert c["monthly_goal"] is None and c["goal_progress"] is None
    assert len(c["daily_income"]) == 30
    assert c["daily_income"][-1] == {"date": date.today().isoformat(), "amount": "250.00"}
    assert c["new_patients_month"] >= 1

    r = await client.put("/api/v1/dashboard/goal", json={"monthly_goal": "1000"}, headers=admin)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["monthly_goal"] == "1000.00"
    assert abs(c["goal_progress"] - 0.25) < 1e-9
    assert c["workdays_left"] >= 0
    if c["workdays_left"]:
        assert c["needed_per_workday"] is not None

    # Quitar la meta.
    c = (await client.put("/api/v1/dashboard/goal", json={"monthly_goal": None}, headers=admin)).json()
    assert c["monthly_goal"] is None


async def test_sin_permiso_de_pagos_no_ve_dinero(client):
    odonto = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    c = (await client.get("/api/v1/dashboard/control", headers=odonto)).json()
    assert c["collected_month"] is None and c["daily_income"] is None
    r = await client.put("/api/v1/dashboard/goal", json={"monthly_goal": "500"}, headers=odonto)
    assert r.status_code == 403
