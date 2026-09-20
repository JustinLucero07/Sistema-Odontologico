"""Phase 9: inventory and laboratory.

The inventory tests are about one idea: stock is the sum of a ledger, so it can
never disagree with its own history and can never go negative. The laboratory
tests are about a case only moving forward, with every step recorded.
"""

from decimal import Decimal


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _item(client, token, name="Guantes de nitrilo M", minimum="2") -> dict:
    response = await client.post(
        "/api/v1/inventory/items",
        json={"name": name, "unit": "caja", "minimum_stock": minimum},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _move(client, token, item_id, reason, qty, **extra):
    return await client.post(
        f"/api/v1/inventory/items/{item_id}/movements",
        json={"reason": reason, "quantity": str(qty), **extra},
        headers=_auth(token),
    )


# ---- Inventory ----------------------------------------------------------


async def test_stock_is_the_sum_of_its_movements(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token)
    assert Decimal(item["on_hand"]) == Decimal("0.000")

    await _move(client, token, item["id"], "compra", 10)
    await _move(client, token, item["id"], "consumo", 3)
    response = await _move(client, token, item["id"], "merma", "0.5")

    assert Decimal(response.json()["on_hand"]) == Decimal("6.500")


async def test_the_reason_fixes_the_direction(client, clinic_with_users):
    """A negative quantity is not a way to sneak a withdrawal past an entry:
    quantities are always positive and the reason decides the sign."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token)

    response = await _move(client, token, item["id"], "compra", -5)
    assert response.status_code == 422


async def test_stock_cannot_go_negative(client, clinic_with_users):
    """A count below zero means the records and the shelf disagree — that is a
    problem to look at, not a number to store."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token)
    await _move(client, token, item["id"], "compra", 2)

    response = await _move(client, token, item["id"], "consumo", 5)
    assert response.status_code == 422
    assert "existencias suficientes" in response.json()["detail"]
    assert "quedan 2.000" in response.json()["detail"]


async def test_a_mistake_is_corrected_by_an_opposite_movement(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token)
    await _move(client, token, item["id"], "compra", 100)  # typed a zero too many
    corrected = await _move(client, token, item["id"], "ajuste_negativo", 90, notes="Error de carga")

    assert Decimal(corrected.json()["on_hand"]) == Decimal("10.000")
    # Both movements survive: the correction is itself inventory history.
    movements = (
        await client.get(
            f"/api/v1/inventory/movements?item_id={item['id']}", headers=_auth(token)
        )
    ).json()
    assert len(movements) == 2


async def test_below_minimum_shows_up_in_the_alerts(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token, minimum="5")
    await _move(client, token, item["id"], "compra", 3)

    alerts = (await client.get("/api/v1/inventory/alerts", headers=_auth(token))).json()
    names = [i["name"] for i in alerts["below_minimum"]]
    assert "Guantes de nitrilo M" in names


async def test_expiry_follows_the_lot_that_is_still_in_stock(client, clinic_with_users):
    """A lot that was fully used up must not keep raising an expiry alarm."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token, name="Anestesia lidocaína", minimum="0")

    await _move(client, token, item["id"], "compra", 4, lot_number="L-1", expires_on="2020-01-01")
    alerts = (await client.get("/api/v1/inventory/alerts", headers=_auth(token))).json()
    assert any(i["name"] == "Anestesia lidocaína" for i in alerts["expired"])

    # Withdraw the whole expired lot; it should stop being reported.
    await _move(client, token, item["id"], "vencimiento", 4, lot_number="L-1", expires_on="2020-01-01")
    alerts = (await client.get("/api/v1/inventory/alerts", headers=_auth(token))).json()
    assert not any(i["name"] == "Anestesia lidocaína" for i in alerts["expired"])


async def test_movements_have_no_delete_endpoint(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    item = await _item(client, token)
    await _move(client, token, item["id"], "compra", 1)
    movements = (
        await client.get(f"/api/v1/inventory/movements?item_id={item['id']}", headers=_auth(token))
    ).json()

    deleted = await client.delete(
        f"/api/v1/inventory/movements/{movements[0]['id']}", headers=_auth(token)
    )
    assert deleted.status_code in (404, 405)


# ---- Laboratory ---------------------------------------------------------


async def _lab(client, token, turnaround=7) -> str:
    response = await client.post(
        "/api/v1/laboratory/laboratories",
        json={"name": "Laboratorio Dental Sur", "default_turnaround_days": turnaround},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _patient(client, token) -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": "Nuria", "last_name": "Vidal"}, headers=_auth(token)
    )
    return created.json()["id"]


async def _order(client, token, lab_id, patient_id, **extra) -> dict:
    response = await client.post(
        "/api/v1/laboratory/orders",
        json={
            "patient_id": patient_id,
            "laboratory_id": lab_id,
            "work_type": "corona",
            "description": "Corona de zirconio 16",
            "fdi_numbers": ["16"],
            **extra,
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_due_date_defaults_to_the_lab_turnaround(client, clinic_with_users):
    from datetime import date, timedelta

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token, turnaround=10)
    order = await _order(client, token, lab_id, await _patient(client, token))

    assert order["due_on"] == str(date.today() + timedelta(days=10))


async def test_status_chain_only_moves_forward(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token)
    order = await _order(client, token, lab_id, await _patient(client, token))

    for step in ["enviado", "en_proceso", "recibido"]:
        response = await client.put(
            f"/api/v1/laboratory/orders/{order['id']}/status",
            json={"status": step},
            headers=_auth(token),
        )
        assert response.status_code == 200, response.text

    back = await client.put(
        f"/api/v1/laboratory/orders/{order['id']}/status",
        json={"status": "enviado"},
        headers=_auth(token),
    )
    assert back.status_code == 400
    assert "rechazado" in back.json()["detail"]


async def test_every_step_is_kept_as_an_event(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token)
    order = await _order(client, token, lab_id, await _patient(client, token))

    await client.put(
        f"/api/v1/laboratory/orders/{order['id']}/status",
        json={"status": "enviado", "note": "Entregado al mensajero"},
        headers=_auth(token),
    )
    final = await client.put(
        f"/api/v1/laboratory/orders/{order['id']}/status",
        json={"status": "en_proceso"},
        headers=_auth(token),
    )

    events = final.json()["events"]
    assert [e["status"] for e in events] == ["borrador", "enviado", "en_proceso"]
    assert events[1]["note"] == "Entregado al mensajero"
    assert final.json()["sent_on"] is not None


async def test_rejection_sends_the_case_back_out(client, clinic_with_users):
    """A crown that came back wrong is no longer in the clinic, so the received
    date has to be cleared — otherwise it looks like it is on the shelf."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token)
    order = await _order(client, token, lab_id, await _patient(client, token))

    for step in ["enviado", "en_proceso", "recibido"]:
        await client.put(
            f"/api/v1/laboratory/orders/{order['id']}/status",
            json={"status": step},
            headers=_auth(token),
        )
    rejected = await client.put(
        f"/api/v1/laboratory/orders/{order['id']}/status",
        json={"status": "rechazado", "note": "Color no coincide"},
        headers=_auth(token),
    )
    assert rejected.json()["received_on"] is None
    assert rejected.json()["status"] == "rechazado"


async def test_an_installed_case_is_closed(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token)
    order = await _order(client, token, lab_id, await _patient(client, token))

    for step in ["enviado", "en_proceso", "recibido", "probado", "instalado"]:
        await client.put(
            f"/api/v1/laboratory/orders/{order['id']}/status",
            json={"status": step},
            headers=_auth(token),
        )
    again = await client.put(
        f"/api/v1/laboratory/orders/{order['id']}/status",
        json={"status": "rechazado"},
        headers=_auth(token),
    )
    assert again.status_code == 409


async def test_overdue_is_derived_and_only_for_open_cases(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token)
    patient_id = await _patient(client, token)
    order = await _order(client, token, lab_id, patient_id, due_on="2020-01-01")

    listing = (await client.get("/api/v1/laboratory/orders", headers=_auth(token))).json()
    found = next(o for o in listing if o["id"] == order["id"])
    assert found["days_overdue"] is not None and found["days_overdue"] > 0

    # Once it is back in the clinic it is no longer late at the lab.
    for step in ["enviado", "en_proceso", "recibido"]:
        await client.put(
            f"/api/v1/laboratory/orders/{order['id']}/status",
            json={"status": step},
            headers=_auth(token),
        )
    listing = (await client.get("/api/v1/laboratory/orders", headers=_auth(token))).json()
    found = next(o for o in listing if o["id"] == order["id"])
    assert found["days_overdue"] is None


async def test_invalid_fdi_on_a_lab_order_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    lab_id = await _lab(client, token)
    response = await client.post(
        "/api/v1/laboratory/orders",
        json={
            "patient_id": await _patient(client, token),
            "laboratory_id": lab_id,
            "work_type": "corona",
            "description": "Corona",
            "fdi_numbers": ["16", "99"],
        },
        headers=_auth(token),
    )
    assert response.status_code == 422
