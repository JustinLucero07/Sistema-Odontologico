"""Oportunidades y huecos libres: reglas claras sobre datos reales."""

from datetime import date, datetime, timedelta, timezone


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _patient(client, h, **extra):
    body = {"first_name": "Ana", "last_name": "Mora", "phone": "0999000111", **extra}
    return (await client.post("/api/v1/patients", json=body, headers=h)).json()["id"]


async def _prof(client, h):
    return (await client.post("/api/v1/professionals", json={"first_name": "Luis", "last_name": "Paz"}, headers=h)).json()["id"]


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def test_opportunities_lists_each_rule(client, clinic_with_users):
    h = await _h(client)
    prof = await _prof(client, h)

    # Cumpleaños mañana
    tomorrow = date.today() + timedelta(days=1)
    bday = await _patient(client, h, first_name="Cumple", birth_date=tomorrow.replace(year=1990).isoformat())

    # Deudor
    debtor = await _patient(client, h, first_name="Deudor")
    await client.post(f"/api/v1/patients/{debtor}/charges", json={"description": "Corona", "amount": "300"}, headers=h)

    # Tratamiento aprobado sin cita
    treat = (await client.post("/api/v1/treatments", json={"name": "Resina", "default_price": 40}, headers=h)).json()
    pending = await _patient(client, h, first_name="Pendiente")
    plan = (await client.post(f"/api/v1/patients/{pending}/treatment-plans", json={"title": "P", "items": []}, headers=h)).json()
    await client.post(
        f"/api/v1/treatment-plans/{plan['id']}/items",
        json={"treatment_id": treat["id"], "price": 40, "discount": 0, "status": "aprobado"},
        headers=h,
    )

    # Cita de mañana sin confirmar
    unconf = await _patient(client, h, first_name="SinConfirmar")
    start = datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=1)
    await client.post(
        "/api/v1/appointments",
        json={"patient_id": unconf, "professional_id": prof, "starts_at": _iso(start), "ends_at": _iso(start + timedelta(minutes=30))},
        headers=h,
    )

    r = await client.get("/api/v1/insights/opportunities", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert any(b["patient_id"] == bday and b["days_until"] == 1 for b in d["birthdays"])
    assert any(x["patient_id"] == debtor and x["pending"] == "300.00" for x in d["debtors"])
    assert any(x["patient_id"] == pending and x["treatments"] == ["Resina"] for x in d["pending_treatments"])
    assert all(x["contact_allowed"] for x in d["debtors"])
    assert d["clinic_name"]

    # Al retirar la autorización de comunicaciones ya no se ofrece contactar.
    await client.post(
        f"/api/v1/patients/{debtor}/privacy/consents",
        json={"kind": "comunicaciones", "granted": False, "method": "verbal"},
        headers=h,
    )
    d = (await client.get("/api/v1/insights/opportunities", headers=h)).json()
    assert next(x for x in d["debtors"] if x["patient_id"] == debtor)["contact_allowed"] is False


async def test_dentist_without_payments_does_not_see_debtors(client, clinic_with_users):
    admin = await _h(client)
    p = await _patient(client, admin)
    await client.post(f"/api/v1/patients/{p}/charges", json={"description": "X", "amount": "10"}, headers=admin)
    dentist = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    r = await client.get("/api/v1/insights/opportunities", headers=dentist)
    assert r.status_code == 200
    assert r.json()["debtors"] == []


async def test_free_slots_skip_busy_times(client, clinic_with_users):
    h = await _h(client)
    prof = await _prof(client, h)
    p = await _patient(client, h)
    day = date.today() + timedelta(days=2)
    if day.weekday() == 6:
        day += timedelta(days=1)

    slots = (await client.get(f"/api/v1/insights/free-slots?professional_id={prof}&date_from={day}&days=1&limit=60", headers=h)).json()
    assert slots, "un día laborable vacío tiene huecos"
    first = datetime.fromisoformat(slots[0]["starts_at"])

    # Se ocupa el primer hueco: deja de ofrecerse.
    await client.post(
        "/api/v1/appointments",
        json={"patient_id": p, "professional_id": prof, "starts_at": _iso(first), "ends_at": _iso(first + timedelta(minutes=30))},
        headers=h,
    )
    again = (await client.get(f"/api/v1/insights/free-slots?professional_id={prof}&date_from={day}&days=1&limit=60", headers=h)).json()
    assert slots[0]["starts_at"] not in [s["starts_at"] for s in again]
    assert len(again) == len(slots) - 1
