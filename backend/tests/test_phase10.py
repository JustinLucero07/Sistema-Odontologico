"""Phase 10: reports.

A report's job is to be believed, so these tests are mostly about denominators
and about what a report refuses to claim: no rate when there is nothing to
divide, no future appointment counted as a no-show, no pending budget counted
as a rejection, and a voided payment reopening the debt it had settled.
"""

from datetime import date, timedelta
from decimal import Decimal


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _patient(client, token, first_name="Iván") -> str:
    created = await client.post(
        "/api/v1/patients",
        json={"first_name": first_name, "last_name": "Nieto"},
        headers=_auth(token),
    )
    return created.json()["id"]


def _range(days_back: int = 30) -> str:
    today = date.today()
    return f"date_from={today - timedelta(days=days_back)}&date_to={today}"


# ---- Financial ----------------------------------------------------------


async def test_collected_counts_only_live_payments(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)

    charge = (
        await client.post(
            f"/api/v1/patients/{patient_id}/charges",
            json={"description": "Corona", "amount": "500.00"},
            headers=_auth(token),
        )
    ).json()
    first = (
        await client.post(
            f"/api/v1/patients/{patient_id}/payments",
            json={"amount": "200.00", "method": "efectivo", "charge_id": charge["id"]},
            headers=_auth(token),
        )
    ).json()
    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "100.00", "method": "efectivo", "charge_id": charge["id"]},
        headers=_auth(token),
    )

    report = (
        await client.get(f"/api/v1/reports/financial?{_range()}", headers=_auth(token))
    ).json()
    assert Decimal(report["collected"]) == Decimal("300.00")
    assert Decimal(report["outstanding_total"]) == Decimal("200.00")

    # Voiding one payment must both lower the take and reopen the debt.
    await client.post(
        f"/api/v1/finance/payments/{first['id']}/void",
        json={"reason": "Cobrado dos veces"},
        headers=_auth(token),
    )
    report = (
        await client.get(f"/api/v1/reports/financial?{_range()}", headers=_auth(token))
    ).json()
    assert Decimal(report["collected"]) == Decimal("100.00")
    assert Decimal(report["outstanding_total"]) == Decimal("400.00")
    assert report["voided_count"] == 1


async def test_receivables_are_bucketed_by_age(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)

    today = date.today()
    await client.post(
        f"/api/v1/patients/{patient_id}/charges",
        json={"description": "Reciente", "amount": "100.00", "issued_on": str(today)},
        headers=_auth(token),
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/charges",
        json={
            "description": "Vieja",
            "amount": "250.00",
            "issued_on": str(today - timedelta(days=200)),
        },
        headers=_auth(token),
    )

    report = (
        await client.get(f"/api/v1/reports/financial?{_range()}", headers=_auth(token))
    ).json()
    buckets = {b["label"]: b for b in report["aging"]}
    assert Decimal(buckets["0–30 días"]["amount"]) == Decimal("100.00")
    assert Decimal(buckets["Más de 90 días"]["amount"]) == Decimal("250.00")


async def test_financial_csv_is_readable_by_a_spreadsheet(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "75.50", "method": "efectivo"},
        headers=_auth(token),
    )

    response = await client.get(f"/api/v1/reports/financial.csv?{_range()}", headers=_auth(token))
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]

    body = response.text
    assert body.startswith("﻿")          # Excel needs the BOM for accents
    assert "sep=;" in body                     # and the separator declared
    assert "75,50" in body                     # decimal comma, like the locale


# ---- Appointments -------------------------------------------------------


async def _professional(client, token) -> str:
    response = await client.post(
        "/api/v1/professionals",
        json={"first_name": "Ana", "last_name": "Molina"},
        headers=_auth(token),
    )
    return response.json()["id"]


async def _appointment(client, token, patient_id, professional_id, when, status_code=None):
    created = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": when.isoformat(),
            "ends_at": (when + timedelta(minutes=30)).isoformat(),
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    appointment_id = created.json()["id"]
    if status_code:
        await client.put(
            f"/api/v1/appointments/{appointment_id}/status",
            json={"status": status_code},
            headers=_auth(token),
        )
    return appointment_id


async def test_future_appointments_do_not_count_as_no_shows(client, clinic_with_users):
    """A slot next week has not failed to happen — it has not happened."""
    from datetime import datetime, timezone

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    professional_id = await _professional(client, token)

    base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    await _appointment(client, token, patient_id, professional_id, base - timedelta(days=3), "atendida")
    await _appointment(client, token, patient_id, professional_id, base - timedelta(days=2), "no_asistio")
    # Still scheduled: it must not enter the denominator.
    await _appointment(client, token, patient_id, professional_id, base + timedelta(days=5))

    report = (
        await client.get(
            f"/api/v1/reports/appointments?date_from={date.today() - timedelta(days=10)}"
            f"&date_to={date.today() + timedelta(days=10)}",
            headers=_auth(token),
        )
    ).json()
    assert report["total"] == 3
    assert report["concluded"] == 2
    assert report["no_show_rate"] == 50.0


async def test_no_rate_when_there_is_nothing_to_divide(client, clinic_with_users):
    """A clinic with no concluded appointments has an UNKNOWN no-show rate,
    not a perfect one."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    report = (
        await client.get(f"/api/v1/reports/appointments?{_range()}", headers=_auth(token))
    ).json()
    assert report["total"] == 0
    assert report["no_show_rate"] is None
    assert report["cancellation_rate"] is None


# ---- Clinical -----------------------------------------------------------


async def test_conversion_rate_ignores_budgets_still_open(client, clinic_with_users):
    """Counting a proposal nobody has answered as a rejection would punish a
    clinic for having work in flight."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    treatment = (
        await client.post(
            "/api/v1/treatments",
            json={"name": "Limpieza", "base_price": 50},
            headers=_auth(token),
        )
    ).json()

    async def make_budget(status: str | None):
        plan = (
            await client.post(
                f"/api/v1/patients/{patient_id}/treatment-plans",
                json={"title": "Plan", "items": [{"treatment_id": treatment["id"], "price": 50}]},
                headers=_auth(token),
            )
        ).json()
        budget = (
            await client.post(
                f"/api/v1/patients/{patient_id}/budgets",
                json={"treatment_plan_id": plan["id"]},
                headers=_auth(token),
            )
        ).json()
        if status:
            await client.put(
                f"/api/v1/budgets/{budget['id']}/status",
                json={"status": status},
                headers=_auth(token),
            )

    await make_budget("aceptado")
    await make_budget("aceptado")
    await make_budget("rechazado")
    await make_budget(None)  # still open

    report = (
        await client.get(f"/api/v1/reports/clinical?{_range()}", headers=_auth(token))
    ).json()
    budgets = report["budgets"]
    assert budgets["accepted_count"] == 2
    assert budgets["rejected_count"] == 1
    assert budgets["pending_count"] == 1
    # 2 of 3 DECIDED, not 2 of 4.
    assert budgets["conversion_rate"] == 66.7


# ---- Patients -----------------------------------------------------------


async def test_dormant_patients_are_those_without_a_recent_visit(client, clinic_with_users):
    from datetime import datetime, timezone

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    seen = await _patient(client, token, "Visto")
    never = await _patient(client, token, "Olvidado")
    professional_id = await _professional(client, token)
    await _appointment(
        client,
        token,
        seen,
        professional_id,
        datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        - timedelta(days=20),
        "atendida",
    )

    report = (
        await client.get(f"/api/v1/reports/patients?{_range()}", headers=_auth(token))
    ).json()
    assert report["seen_last_12m"] == 1
    assert report["dormant"] == report["total_active"] - 1
    assert report["new_patients"] == 2


# ---- Range guards -------------------------------------------------------


async def test_backwards_range_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    response = await client.get(
        "/api/v1/reports/summary?date_from=2026-12-01&date_to=2026-01-01", headers=_auth(token)
    )
    assert response.status_code == 400


async def test_absurd_range_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    response = await client.get(
        "/api/v1/reports/summary?date_from=2019-01-01&date_to=2026-01-01", headers=_auth(token)
    )
    assert response.status_code == 400


async def test_summary_defaults_to_the_last_30_days(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    report = (await client.get("/api/v1/reports/summary", headers=_auth(token))).json()
    assert report["range"]["date_to"] == str(date.today())
    assert report["range"]["date_from"] == str(date.today() - timedelta(days=29))
