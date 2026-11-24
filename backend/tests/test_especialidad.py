from datetime import date, datetime, timedelta, timezone


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _foco(client, h, foco):
    r = await client.put("/api/v1/clinics/me", json={"specialty_focus": foco}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def test_general_no_muestra_franja(client):
    h = await _h(client)
    assert (await client.get("/api/v1/clinics/branding", headers=h)).json()["specialty_focus"] == "general"
    assert (await client.get("/api/v1/dashboard/specialty", headers=h)).json() is None


async def test_especialidad_invalida(client):
    h = await _h(client)
    assert (await client.put("/api/v1/clinics/me", json={"specialty_focus": "cardiologia"}, headers=h)).status_code == 422


async def test_ortodoncia_activa_el_modulo(client):
    h = await _h(client)
    c = await _foco(client, h, "ortodoncia")
    assert c["orthodontics_enabled"] is True
    b = (await client.get("/api/v1/clinics/branding", headers=h)).json()
    assert b["specialty_focus"] == "ortodoncia" and b["orthodontics_enabled"] is True
    d = (await client.get("/api/v1/dashboard/specialty", headers=h)).json()
    assert d["foco"] == "ortodoncia"
    assert {c["codigo"] for c in d["cifras"]} == {"hoy", "semana", "atrasados", "activos"}


async def test_pediatria_cuenta_ninos_de_hoy(client):
    h = await _h(client)
    await _foco(client, h, "pediatria")
    nac = (date.today() - timedelta(days=365 * 7 + 30)).isoformat()
    nino = (await client.post("/api/v1/patients", json={"first_name": "Tomás", "last_name": "Ruiz", "birth_date": nac}, headers=h)).json()["id"]
    await client.post("/api/v1/patients", json={"first_name": "Adulto", "last_name": "Uno", "birth_date": "1980-01-01"}, headers=h)
    prof = (await client.post("/api/v1/professionals", json={"first_name": "Ana", "last_name": "Paz"}, headers=h)).json()["id"]
    ini = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(minutes=5)
    r = await client.post(
        "/api/v1/appointments",
        json={"patient_id": nino, "professional_id": prof, "starts_at": ini.isoformat(),
              "ends_at": (ini + timedelta(minutes=30)).isoformat(), "reminder_channels": []},
        headers=h,
    )
    assert r.status_code == 201, r.text
    d = (await client.get("/api/v1/dashboard/specialty", headers=h)).json()
    cifras = {c["codigo"]: c["valor"] for c in d["cifras"]}
    assert cifras["total"] == 1
    if d["lista"]:
        assert d["lista"][0]["nombre"] == "Tomás Ruiz"
        assert d["lista"][0]["detalle"].startswith("7 años")


async def test_estetica_detecta_tratamientos_esteticos(client):
    h = await _h(client)
    await _foco(client, h, "estetica")
    d = (await client.get("/api/v1/dashboard/specialty", headers=h)).json()
    assert d["foco"] == "estetica"
    assert {c["codigo"] for c in d["cifras"]} >= {"propuestos", "curso", "comparaciones", "redes"}
