"""Créditos: financiar un tratamiento en cuotas.

Lo que siempre tiene que cuadrar: el calendario suma exactamente lo
financiado más el interés; cada pago cubre las cuotas de la más antigua a la
más nueva; y el estado de cuenta del paciente coincide con el crédito.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.modules.credits.amortization import schedule


async def _token(client, email="admin@clinicatest.io", password="Admin123!"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup(client, h, amount="600.00"):
    patient_id = (
        await client.post(
            "/api/v1/patients", json={"first_name": "Lucía", "last_name": "Arce", "whatsapp": "+593999"}, headers=h
        )
    ).json()["id"]
    charge = (
        await client.post(
            f"/api/v1/patients/{patient_id}/charges", json={"description": "Ortodoncia", "amount": amount}, headers=h
        )
    ).json()
    return patient_id, charge["id"]


async def _credit(client, h, patient_id, charge_id, **extra):
    body = {
        "charge_id": charge_id,
        "installment_count": 3,
        "frequency": "mensual",
        "first_due_on": (date.today() + timedelta(days=30)).isoformat(),
        **extra,
    }
    return await client.post(f"/api/v1/patients/{patient_id}/credits", json=body, headers=h)


def test_french_schedule_closes_exactly():
    rows = schedule(Decimal("1000.00"), 7, Decimal("2"), 30, date(2026, 1, 1))
    assert sum(r.principal for r in rows) == Decimal("1000.00")
    # Cuota fija: todas iguales salvo el ajuste de centavos de la última.
    assert len({r.amount for r in rows[:-1]}) == 1
    assert abs(rows[-1].amount - rows[0].amount) <= Decimal("0.05")
    # El interés baja a medida que baja el saldo.
    assert rows[0].interest > rows[-1].interest


def test_zero_rate_splits_evenly():
    rows = schedule(Decimal("100.00"), 3, Decimal("0"), 30, date(2026, 1, 1))
    assert [r.amount for r in rows] == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]


async def test_credit_with_down_payment_and_no_interest(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h)
    credit = await _credit(client, h, patient_id, charge_id, down_payment="150.00")
    assert credit.status_code == 201, credit.text
    body = credit.json()
    assert body["principal"] == "450.00"
    assert body["total"] == "450.00"
    assert body["status"] == "al_dia"
    assert [i["amount"] for i in body["installments"]] == ["150.00", "150.00", "150.00"]

    account = (await client.get(f"/api/v1/patients/{patient_id}/account", headers=h)).json()
    assert account["balance"] == "450.00"  # 600 - 150 de entrada


async def test_interest_is_billed_and_payments_split(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h, "1000.00")
    body = (await _credit(client, h, patient_id, charge_id, monthly_rate="2")).json()
    assert Decimal(body["total_interest"]) > 0
    interest_charge_id = body["interest_charge_id"]
    assert interest_charge_id

    first = body["installments"][0]
    paid = (
        await client.post(
            f"/api/v1/credits/{body['id']}/payments",
            json={"amount": first["amount"], "method": "efectivo"},
            headers=h,
        )
    ).json()
    assert paid["installments"][0]["status"] == "pagada"
    assert paid["paid"] == first["amount"]

    account = (await client.get(f"/api/v1/patients/{patient_id}/account", headers=h)).json()
    by_id = {c["id"]: c for c in account["charges"]}
    # El interés de la primera cuota fue al cargo de intereses; el resto, al tratamiento.
    assert by_id[interest_charge_id]["paid"] == first["interest"]
    assert by_id[charge_id]["paid"] == first["principal"]
    # Estado de cuenta y crédito dicen lo mismo.
    assert account["balance"] == paid["pending"]


async def test_overpaying_and_paying_outside_the_credit_are_refused(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h, "300.00")
    body = (await _credit(client, h, patient_id, charge_id)).json()

    too_much = await client.post(
        f"/api/v1/credits/{body['id']}/payments", json={"amount": "301.00", "method": "efectivo"}, headers=h
    )
    assert too_much.status_code == 422

    outside = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "10.00", "method": "efectivo", "charge_id": charge_id},
        headers=h,
    )
    assert outside.status_code == 409


async def test_overdue_installments_are_flagged(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h, "300.00")
    past = (date.today() - timedelta(days=45)).isoformat()
    body = (await _credit(client, h, patient_id, charge_id, first_due_on=past)).json()
    assert body["status"] == "vencido"
    assert body["days_late"] == 45
    assert body["overdue"] == "200.00"  # dos cuotas ya vencidas (hace 45 y 15 días)

    summary = (await client.get("/api/v1/credits/summary", headers=h)).json()
    assert summary["overdue_count"] == 1
    assert (await client.get("/api/v1/credits?status=vencido", headers=h)).json()[0]["id"] == body["id"]

    dashboard = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    assert dashboard["attention"]["credits_overdue"] == 1


async def test_restructure_keeps_paid_and_spreads_the_rest(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h, "300.00")
    body = (await _credit(client, h, patient_id, charge_id)).json()
    await client.post(f"/api/v1/credits/{body['id']}/payments", json={"amount": "130.00", "method": "efectivo"}, headers=h)

    new_first = (date.today() + timedelta(days=60)).isoformat()
    restructured = await client.post(
        f"/api/v1/credits/{body['id']}/restructure",
        json={"installment_count": 4, "frequency": "quincenal", "first_due_on": new_first},
        headers=h,
    )
    assert restructured.status_code == 200, restructured.text
    r = restructured.json()
    assert r["total"] == "300.00"
    assert r["paid"] == "130.00"
    assert r["pending"] == "170.00"
    pending_rows = [i for i in r["installments"] if i["status"] != "pagada"]
    assert len(pending_rows) == 4
    assert sum(Decimal(i["amount"]) for i in pending_rows) == Decimal("170.00")
    assert pending_rows[0]["due_on"] == new_first


async def test_void_only_without_payments_and_it_frees_the_charge(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h, "300.00")
    body = (await _credit(client, h, patient_id, charge_id, monthly_rate="1")).json()

    paid = (
        await client.post(f"/api/v1/credits/{body['id']}/payments", json={"amount": "50.00", "method": "efectivo"}, headers=h)
    ).json()
    blocked = await client.post(f"/api/v1/credits/{body['id']}/void", json={"reason": "Error"}, headers=h)
    assert blocked.status_code == 409

    # Anular un pago de cuota anula sus dos partes (interés y capital).
    first_payment = paid["payments"][0]["payment_ids"][0]
    await client.post(f"/api/v1/finance/payments/{first_payment}/void", json={"reason": "Mal cobrado"}, headers=h)
    detail = (await client.get(f"/api/v1/credits/{body['id']}", headers=h)).json()
    assert detail["paid"] == "0.00"

    voided = await client.post(f"/api/v1/credits/{body['id']}/void", json={"reason": "El paciente pagará de contado"}, headers=h)
    assert voided.status_code == 200
    assert voided.json()["status"] == "anulado"
    # El cargo vuelve a aceptar pagos normales y el interés queda anulado.
    ok = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        json={"amount": "300.00", "method": "efectivo", "charge_id": charge_id},
        headers=h,
    )
    assert ok.status_code == 201
    account = (await client.get(f"/api/v1/patients/{patient_id}/account", headers=h)).json()
    assert account["balance"] == "0.00"


async def test_guarantor_is_editable(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h)
    body = (await _credit(client, h, patient_id, charge_id)).json()
    edited = await client.put(
        f"/api/v1/credits/{body['id']}",
        json={"guarantor_name": "Rosa Arce", "guarantor_id_number": "0102030405", "guarantor_phone": "0999"},
        headers=h,
    )
    assert edited.json()["guarantor_name"] == "Rosa Arce"


async def test_down_payment_cannot_cover_everything(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id, charge_id = await _setup(client, h, "100.00")
    response = await _credit(client, h, patient_id, charge_id, down_payment="100.00")
    assert response.status_code == 422


async def test_credits_need_payment_permissions(client, clinic_with_users):
    dentist = _auth(await _token(client, "dentist@clinicatest.io", "Dentist123!"))
    assert (await client.get("/api/v1/credits", headers=dentist)).status_code == 403
