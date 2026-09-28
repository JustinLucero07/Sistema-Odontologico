"""Finanzas: egresos, resultado del periodo y caja.

Lo que tiene que cuadrar siempre: lo cobrado menos lo gastado es la utilidad,
y el efectivo esperado al cerrar la caja es el fondo más los cobros en
efectivo menos los gastos pagados en efectivo de esa caja.
"""

from datetime import date, timedelta


async def _token(client, email="admin@clinicatest.io", password="Admin123!"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _patient(client, h) -> str:
    return (
        await client.post("/api/v1/patients", json={"first_name": "Lucía", "last_name": "Arce"}, headers=h)
    ).json()["id"]


async def _pay(client, h, patient_id, amount, method="efectivo", charge_id=None):
    body = {"amount": amount, "method": method}
    if charge_id:
        body["charge_id"] = charge_id
    if method != "efectivo":
        body["reference"] = "REF-1"
    response = await client.post(f"/api/v1/patients/{patient_id}/payments", json=body, headers=h)
    assert response.status_code == 201, response.text
    return response.json()


async def _expense(client, h, amount, method="efectivo", **extra):
    body = {
        "spent_on": date.today().isoformat(),
        "category": "insumos",
        "description": "Guantes de nitrilo",
        "amount": amount,
        "method": method,
        **extra,
    }
    response = await client.post("/api/v1/finance/expenses", json=body, headers=h)
    return response


async def test_cash_expenses_come_out_of_the_till(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h)
    await client.post("/api/v1/finance/cash-session/open", json={"opening_float": "50.00"}, headers=h)

    await _pay(client, h, patient_id, "100.00")
    await _pay(client, h, patient_id, "80.00", method="tarjeta_debito")  # no entra al cajón
    assert (await _expense(client, h, "30.00")).status_code == 201
    assert (await _expense(client, h, "200.00", method="transferencia")).status_code == 201  # no sale del cajón

    session = (await client.get("/api/v1/finance/cash-session", headers=h)).json()
    assert session["cash_in"] == "100.00"
    assert session["cash_out"] == "30.00"
    assert session["expected_now"] == "120.00"

    closed = (
        await client.post("/api/v1/finance/cash-session/close", json={"counted_cash": "118.00"}, headers=h)
    ).json()
    assert closed["expected_cash"] == "120.00"
    assert closed["difference"] == "-2.00"

    history = (await client.get("/api/v1/finance/cash-sessions", headers=h)).json()
    assert history[0]["cash_out"] == "30.00"
    assert history[0]["difference"] == "-2.00"


async def test_summary_nets_income_against_expenses(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h)
    charge = (
        await client.post(
            f"/api/v1/patients/{patient_id}/charges", json={"description": "Endodoncia", "amount": "180.00"}, headers=h
        )
    ).json()
    await _pay(client, h, patient_id, "150.00", charge_id=charge["id"])
    await _expense(client, h, "40.00")
    voided = (await _expense(client, h, "999.00")).json()
    await client.post(f"/api/v1/finance/expenses/{voided['id']}/void", json={"reason": "Registrado dos veces"}, headers=h)

    summary = (await client.get("/api/v1/finance/summary", headers=h)).json()
    assert summary["sales"] == "180.00"
    assert summary["income"] == "150.00"
    # El anulado no cuenta.
    assert summary["expenses"] == "40.00"
    assert summary["net"] == "110.00"
    assert summary["receivables"] == "30.00"
    assert summary["expenses_by_category"][0]["code"] == "insumos"
    assert summary["monthly"][-1]["net"] == "110.00"


async def test_expense_amount_is_not_editable_only_its_details(client, clinic_with_users):
    h = _auth(await _token(client))
    expense = (await _expense(client, h, "25.00", method="transferencia")).json()
    edited = await client.put(
        f"/api/v1/finance/expenses/{expense['id']}",
        json={
            "spent_on": date.today().isoformat(),
            "category": "laboratorio",
            "description": "Corona de zirconio",
            "receipt_number": "001-002-000123",
            "amount": "1.00",  # se ignora: el importe no se edita
        },
        headers=h,
    )
    assert edited.status_code == 200
    assert edited.json()["category_label"] == "Laboratorio dental"
    assert edited.json()["receipt_number"] == "001-002-000123"
    assert edited.json()["amount"] == "25.00"


async def test_expense_validation(client, clinic_with_users):
    h = _auth(await _token(client))
    assert (await _expense(client, h, "0")).status_code == 422
    assert (await _expense(client, h, "10.00", category="inventada")).status_code == 422
    assert (await _expense(client, h, "10.00", method="bitcoin")).status_code == 422


async def test_payments_listing_and_csv(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h)
    await _pay(client, h, patient_id, "60.00")
    listed = (await client.get("/api/v1/finance/payments", headers=h)).json()
    assert listed[0]["patient_name"] == "Lucía Arce"
    assert listed[0]["concept"] is None

    csv = await client.get("/api/v1/finance/payments.csv", headers=h)
    assert csv.status_code == 200
    assert "attachment" in csv.headers["content-disposition"]
    assert "60,00" in csv.text

    await _expense(client, h, "12.50")
    assert "12,50" in (await client.get("/api/v1/finance/expenses.csv", headers=h)).text


async def test_expense_on_another_day_does_not_touch_todays_till(client, clinic_with_users):
    h = _auth(await _token(client))
    await client.post("/api/v1/finance/cash-session/open", json={"opening_float": "20.00"}, headers=h)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    await _expense(client, h, "15.00", spent_on=yesterday)
    session = (await client.get("/api/v1/finance/cash-session", headers=h)).json()
    assert session["expected_now"] == "20.00"


async def test_finance_requires_payment_permissions(client, clinic_with_users):
    dentist = _auth(await _token(client, "dentist@clinicatest.io", "Dentist123!"))
    assert (await client.get("/api/v1/finance/summary", headers=dentist)).status_code == 403
    assert (await _expense(client, dentist, "10.00")).status_code == 403
