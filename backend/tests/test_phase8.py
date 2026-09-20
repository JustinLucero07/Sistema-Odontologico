"""Phase 8: charges, payments, instalments and the till.

These tests are about money integrity: that a balance is derived rather than
stored, that nothing is ever deleted, that a charge cannot be billed twice,
and that arithmetic on money does not drift.
"""

from decimal import Decimal


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client, token, first_name="Marta") -> str:
    created = await client.post(
        "/api/v1/patients",
        json={"first_name": first_name, "last_name": "Soler"},
        headers=_auth(token),
    )
    return created.json()["id"]


async def _charge(client, token, patient_id, amount, description="Tratamiento") -> dict:
    response = await client.post(
        f"/api/v1/patients/{patient_id}/charges",
        json={"description": description, "amount": str(amount)},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _pay(client, token, patient_id, amount, **extra):
    body = {"amount": str(amount), "method": "efectivo", **extra}
    return await client.post(
        f"/api/v1/patients/{patient_id}/payments", json=body, headers=_auth(token)
    )


# ---- Statement ----------------------------------------------------------


async def test_balance_is_charges_minus_payments(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    charge = await _charge(client, token, patient_id, "150.00")
    await _pay(client, token, patient_id, "50.00", charge_id=charge["id"])

    account = (
        await client.get(f"/api/v1/patients/{patient_id}/account", headers=_auth(token))
    ).json()
    assert Decimal(account["total_charged"]) == Decimal("150.00")
    assert Decimal(account["total_paid"]) == Decimal("50.00")
    assert Decimal(account["balance"]) == Decimal("100.00")
    assert account["charges"][0]["status"] == "parcial"


async def test_money_arithmetic_does_not_drift(client, clinic_with_users):
    """Three payments of 0.10 against 0.30 must settle the charge exactly.
    In float arithmetic they do not."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    charge = await _charge(client, token, patient_id, "0.30")

    for _ in range(3):
        response = await _pay(client, token, patient_id, "0.10", charge_id=charge["id"])
        assert response.status_code == 201, response.text

    account = (
        await client.get(f"/api/v1/patients/{patient_id}/account", headers=_auth(token))
    ).json()
    assert Decimal(account["balance"]) == Decimal("0.00")
    assert account["charges"][0]["status"] == "pagada"


async def test_overpayment_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    charge = await _charge(client, token, patient_id, "100.00")

    response = await _pay(client, token, patient_id, "120.00", charge_id=charge["id"])
    assert response.status_code == 422
    assert "supera el saldo" in response.json()["detail"]


async def test_payment_on_account_needs_no_charge(client, clinic_with_users):
    """A patient can pay before anything is billed; that money still counts."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await _pay(client, token, patient_id, "80.00")
    assert response.status_code == 201

    account = (
        await client.get(f"/api/v1/patients/{patient_id}/account", headers=_auth(token))
    ).json()
    assert Decimal(account["unallocated"]) == Decimal("80.00")
    assert Decimal(account["balance"]) == Decimal("-80.00")


async def test_card_payment_requires_a_reference(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "40.00", "method": "tarjeta_credito"},
        headers=_auth(token),
    )
    assert response.status_code == 422


# ---- Voiding ------------------------------------------------------------


async def test_voided_payment_stops_counting_but_survives(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    charge = await _charge(client, token, patient_id, "200.00")
    payment = (await _pay(client, token, patient_id, "200.00", charge_id=charge["id"])).json()

    voided = await client.post(
        f"/api/v1/finance/payments/{payment['id']}/void",
        json={"reason": "Cobrado al paciente equivocado"},
        headers=_auth(token),
    )
    assert voided.status_code == 200

    account = (
        await client.get(f"/api/v1/patients/{patient_id}/account", headers=_auth(token))
    ).json()
    assert Decimal(account["balance"]) == Decimal("200.00")
    assert account["charges"][0]["status"] == "pendiente"
    # The row is still there, with its reason.
    assert len(account["payments"]) == 1
    assert account["payments"][0]["void_reason"] == "Cobrado al paciente equivocado"


async def test_void_requires_a_reason(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    payment = (await _pay(client, token, patient_id, "10.00")).json()

    response = await client.post(
        f"/api/v1/finance/payments/{payment['id']}/void",
        json={"reason": ""},
        headers=_auth(token),
    )
    assert response.status_code == 422


async def test_charge_with_live_payments_cannot_be_voided(client, clinic_with_users):
    """Voiding it would leave the payments pointing at nothing."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    charge = await _charge(client, token, patient_id, "90.00")
    await _pay(client, token, patient_id, "30.00", charge_id=charge["id"])

    response = await client.post(
        f"/api/v1/finance/charges/{charge['id']}/void",
        json={"reason": "Error de carga"},
        headers=_auth(token),
    )
    assert response.status_code == 409
    assert "pago" in response.json()["detail"].lower()


async def test_payments_have_no_delete_endpoint(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    payment = (await _pay(client, token, patient_id, "25.00")).json()

    deleted = await client.delete(
        f"/api/v1/finance/payments/{payment['id']}", headers=_auth(token)
    )
    assert deleted.status_code in (404, 405)


# ---- Instalments --------------------------------------------------------


async def test_installments_sum_exactly_to_the_charge(client, clinic_with_users):
    """100 / 3 does not divide evenly; the remainder has to land somewhere or
    the patient is left with a debt they cannot clear."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    charge = await _charge(client, token, patient_id, "100.00")

    response = await client.post(
        f"/api/v1/finance/charges/{charge['id']}/installments",
        json={"count": 3, "first_due_on": "2026-10-01", "every_days": 30},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    rows = response.json()["installments"]
    assert len(rows) == 3
    assert sum(Decimal(r["amount"]) for r in rows) == Decimal("100.00")
    assert [r["due_on"] for r in rows] == ["2026-10-01", "2026-10-31", "2026-11-30"]


async def test_payments_cover_installments_oldest_first(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    charge = await _charge(client, token, patient_id, "300.00")
    await client.post(
        f"/api/v1/finance/charges/{charge['id']}/installments",
        json={"count": 3, "first_due_on": "2026-10-01"},
        headers=_auth(token),
    )
    await _pay(client, token, patient_id, "150.00", charge_id=charge["id"])

    account = (
        await client.get(f"/api/v1/patients/{patient_id}/account", headers=_auth(token))
    ).json()
    rows = account["charges"][0]["installments"]
    assert rows[0]["status"] == "pagada"
    assert Decimal(rows[1]["paid"]) == Decimal("50.00")
    assert rows[1]["status"] == "parcial"
    assert rows[2]["status"] == "pendiente"


# ---- Budget integration -------------------------------------------------


async def test_accepting_a_budget_raises_exactly_one_charge(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    treatment = await client.post(
        "/api/v1/treatments",
        json={"name": "Corona", "base_price": 400},
        headers=_auth(token),
    )
    plan = await client.post(
        f"/api/v1/patients/{patient_id}/treatment-plans",
        json={"title": "Plan", "items": [{"treatment_id": treatment.json()["id"], "price": 400}]},
        headers=_auth(token),
    )
    budget = await client.post(
        f"/api/v1/patients/{patient_id}/budgets",
        json={"treatment_plan_id": plan.json()["id"]},
        headers=_auth(token),
    )
    budget_id = budget.json()["id"]

    for _ in range(2):  # accepting twice must not bill twice
        response = await client.put(
            f"/api/v1/budgets/{budget_id}/status",
            json={"status": "aceptado"},
            headers=_auth(token),
        )
        assert response.status_code == 200, response.text

    account = (
        await client.get(f"/api/v1/patients/{patient_id}/account", headers=_auth(token))
    ).json()
    assert len(account["charges"]) == 1
    assert account["charges"][0]["budget_id"] == budget_id
    assert Decimal(account["total_charged"]) == Decimal("400.00")


# ---- Till ---------------------------------------------------------------


async def test_cash_session_reconciles_against_counted_cash(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    opened = await client.post(
        "/api/v1/finance/cash-session/open",
        json={"opening_float": "50.00"},
        headers=_auth(token),
    )
    assert opened.status_code == 201

    await _pay(client, token, patient_id, "120.00")
    # A card payment never enters the till, so it must not be expected there.
    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "60.00", "method": "tarjeta_credito", "reference": "1234"},
        headers=_auth(token),
    )

    closed = await client.post(
        "/api/v1/finance/cash-session/close",
        json={"counted_cash": "168.00"},
        headers=_auth(token),
    )
    body = closed.json()
    assert Decimal(body["expected_cash"]) == Decimal("170.00")  # 50 float + 120 cash
    assert Decimal(body["difference"]) == Decimal("-2.00")  # two short, and recorded
    assert body["is_open"] is False


async def test_only_one_till_open_at_a_time(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    await client.post(
        "/api/v1/finance/cash-session/open", json={"opening_float": "0"}, headers=_auth(token)
    )
    second = await client.post(
        "/api/v1/finance/cash-session/open", json={"opening_float": "0"}, headers=_auth(token)
    )
    assert second.status_code == 409


async def test_daily_report_breaks_down_by_method(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    await _pay(client, token, patient_id, "100.00")
    await _pay(client, token, patient_id, "40.00")
    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "75.50", "method": "transferencia", "reference": "TRF-9"},
        headers=_auth(token),
    )

    report = (await client.get("/api/v1/finance/daily-report", headers=_auth(token))).json()
    assert Decimal(report["total"]) == Decimal("215.50")
    assert report["payment_count"] == 3
    by = {b["method"]: b for b in report["by_method"]}
    assert Decimal(by["efectivo"]["total"]) == Decimal("140.00")
    assert by["efectivo"]["count"] == 2
    assert Decimal(by["transferencia"]["total"]) == Decimal("75.50")
