"""El panel principal: "hoy" es el día de la clínica, y el dinero solo lo ve
quien tiene permiso para verlo."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CLINIC_TZ = ZoneInfo("America/Guayaquil")  # la zona por defecto de una clínica


async def _token(client, email="admin@clinicatest.io", password="Admin123!"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup(client, h, **patient):
    patient_id = (
        await client.post(
            "/api/v1/patients", json={"first_name": "Lucía", "last_name": "Arce", **patient}, headers=h
        )
    ).json()["id"]
    professional_id = (
        await client.post("/api/v1/professionals", json={"first_name": "Ana", "last_name": "Molina"}, headers=h)
    ).json()["id"]
    return patient_id, professional_id


async def _book(client, h, patient_id, professional_id, when: datetime):
    created = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": when.isoformat(),
            "ends_at": (when + timedelta(minutes=30)).isoformat(),
        },
        headers=h,
    )
    assert created.status_code == 201, created.text


async def test_today_is_the_clinic_day_not_the_utc_day(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, professional_id = await _setup(client, h)
    local_today = datetime.now(CLINIC_TZ).date()

    # 22:00 en Ecuador ya es el día siguiente en UTC; sigue siendo "hoy".
    await _book(client, h, patient_id, professional_id, datetime.combine(local_today, time(22, 0), CLINIC_TZ))
    # 01:00 de mañana en Ecuador todavía es "hoy" en UTC; no es de hoy.
    await _book(
        client, h, patient_id, professional_id,
        datetime.combine(local_today + timedelta(days=1), time(1, 0), CLINIC_TZ),
    )

    summary = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    assert summary["today"] == local_today.isoformat()
    assert summary["appointments_today"] == 1
    assert len(summary["today_agenda"]) == 1
    assert summary["today_agenda"][0]["patient_name"] == "Lucía Arce"
    by_day = {d["date"]: d["count"] for d in summary["appointments_per_day"]}
    assert by_day[local_today.isoformat()] == 1
    assert by_day[(local_today + timedelta(days=1)).isoformat()] == 1


async def test_money_is_hidden_without_payment_permission(client, clinic_with_users):
    admin = (await client.get("/api/v1/dashboard/summary", headers=_auth(await _token(client)))).json()
    assert admin["income_month"] == "0.00"
    assert admin["receivables_total"] == "0.00"

    dentist_token = await _token(client, "dentist@clinicatest.io", "Dentist123!")
    dentist = (await client.get("/api/v1/dashboard/summary", headers=_auth(dentist_token))).json()
    # None, no cero: cero diría "no se cobró nada", y eso no lo sabe.
    assert dentist["income_month"] is None
    assert dentist["receivables_total"] is None


async def test_income_counts_only_live_payments_this_month(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, _ = await _setup(client, h)
    methods = (await client.get("/api/v1/finance/payment-methods", headers=h)).json()
    method = methods[0]["code"] if isinstance(methods[0], dict) else methods[0]
    await client.post("/api/v1/finance/cash-session/open", json={"opening_amount": "0"}, headers=h)

    async def pay(amount: str):
        response = await client.post(
            f"/api/v1/patients/{patient_id}/payments", json={"amount": amount, "method": method}, headers=h
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    await pay("40.00")
    voided = await pay("25.00")
    await client.post(f"/api/v1/finance/payments/{voided}/void", json={"reason": "Cobrado dos veces"}, headers=h)

    summary = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    assert summary["income_month"] == "40.00"


async def test_birthdays_today_are_listed(client, clinic_with_users):
    h = _auth(await _token(client))
    today = datetime.now(CLINIC_TZ).date()
    try:
        birth = today.replace(year=today.year - 30)
    except ValueError:  # 29 de febrero
        birth = date(today.year - 30, 3, 1)
    await _setup(client, h, birth_date=birth.isoformat(), whatsapp="+593999000111")

    summary = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    birthdays = summary["attention"]["birthdays"]
    if birth.month == today.month and birth.day == today.day:
        assert len(birthdays) == 1
        assert birthdays[0]["turns"] == 30
        assert birthdays[0]["whatsapp"] == "+593999000111"


async def test_overdue_lab_work_is_flagged(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, _ = await _setup(client, h)
    lab = (await client.post("/api/v1/laboratory/laboratories", json={"name": "Lab"}, headers=h)).json()
    yesterday = (datetime.now(CLINIC_TZ).date() - timedelta(days=1)).isoformat()
    await client.post(
        "/api/v1/laboratory/orders",
        json={
            "patient_id": patient_id, "laboratory_id": lab["id"], "work_type": "corona",
            "description": "Corona 16", "due_on": yesterday,
        },
        headers=h,
    )
    summary = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    assert summary["attention"]["lab_overdue"] == 1
