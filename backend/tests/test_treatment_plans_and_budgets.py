async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client, token) -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": "Elena", "last_name": "Ríos"}, headers=_auth(token)
    )
    return created.json()["id"]


async def _create_treatment(client, token, name="Restauración", price=45.0) -> str:
    created = await client.post(
        "/api/v1/treatments", json={"name": name, "default_price": price}, headers=_auth(token)
    )
    return created.json()["id"]


async def test_create_diagnosis(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        json={"fdi_number": "16", "description": "Caries oclusal profunda"},
        headers=_auth(token),
    )
    assert response.status_code == 201
    assert response.json()["description"] == "Caries oclusal profunda"

    listing = await client.get(f"/api/v1/patients/{patient_id}/diagnoses", headers=_auth(token))
    assert len(listing.json()) == 1


async def test_treatment_catalog_crud(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    treatment_id = await _create_treatment(client, token)

    listing = await client.get("/api/v1/treatments", headers=_auth(token))
    assert any(t["id"] == treatment_id for t in listing.json())

    updated = await client.put(
        f"/api/v1/treatments/{treatment_id}", json={"default_price": 60.0}, headers=_auth(token)
    )
    assert updated.status_code == 200
    assert updated.json()["default_price"] == 60.0


async def test_treatment_plan_progress_and_items(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    treatment_id = await _create_treatment(client, token)

    plan = await client.post(
        f"/api/v1/patients/{patient_id}/treatment-plans",
        json={
            "title": "Plan inicial",
            "items": [
                {"treatment_id": treatment_id, "fdi_number": "16", "price": 45.0, "status": "propuesto"},
                {"treatment_id": treatment_id, "fdi_number": "26", "price": 45.0, "status": "propuesto"},
            ],
        },
        headers=_auth(token),
    )
    assert plan.status_code == 201
    plan_body = plan.json()
    assert len(plan_body["items"]) == 2
    assert plan_body["progress_percent"] == 0.0
    assert plan_body["total_price"] == 90.0

    plan_id = plan_body["id"]
    item_id = plan_body["items"][0]["id"]

    completed = await client.put(
        f"/api/v1/treatment-plans/{plan_id}/items/{item_id}",
        json={"status": "completado"},
        headers=_auth(token),
    )
    assert completed.status_code == 200
    assert completed.json()["progress_percent"] == 50.0
    # completing an item auto-stamps a completed_date when none was given
    completed_item = next(i for i in completed.json()["items"] if i["id"] == item_id)
    assert completed_item["completed_date"] is not None

    # a cancelled item is excluded from the progress denominator entirely
    other_item_id = plan_body["items"][1]["id"]
    cancelled = await client.put(
        f"/api/v1/treatment-plans/{plan_id}/items/{other_item_id}",
        json={"status": "cancelado"},
        headers=_auth(token),
    )
    assert cancelled.json()["progress_percent"] == 100.0


async def test_budget_auto_generated_from_plan_and_totals(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    treatment_id = await _create_treatment(client, token, price=100.0)

    plan = await client.post(
        f"/api/v1/patients/{patient_id}/treatment-plans",
        json={"items": [{"treatment_id": treatment_id, "price": 100.0, "discount": 10.0}]},
        headers=_auth(token),
    )
    plan_id = plan.json()["id"]

    budget = await client.post(
        f"/api/v1/patients/{patient_id}/budgets",
        json={"treatment_plan_id": plan_id, "tax_rate": 15},
        headers=_auth(token),
    )
    assert budget.status_code == 201
    body = budget.json()
    assert body["status"] == "borrador"
    assert len(body["items"]) == 1
    assert body["subtotal"] == 90.0
    assert body["tax_amount"] == 13.5
    assert body["total"] == 103.5


async def test_budget_status_cannot_go_backwards(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    treatment_id = await _create_treatment(client, token)

    plan = await client.post(
        f"/api/v1/patients/{patient_id}/treatment-plans",
        json={"items": [{"treatment_id": treatment_id, "price": 50.0}]},
        headers=_auth(token),
    )
    plan_id = plan.json()["id"]
    budget = await client.post(
        f"/api/v1/patients/{patient_id}/budgets", json={"treatment_plan_id": plan_id}, headers=_auth(token)
    )
    budget_id = budget.json()["id"]

    sent = await client.put(f"/api/v1/budgets/{budget_id}/status", json={"status": "enviado"}, headers=_auth(token))
    assert sent.status_code == 200

    backwards = await client.put(
        f"/api/v1/budgets/{budget_id}/status", json={"status": "borrador"}, headers=_auth(token)
    )
    assert backwards.status_code == 400

    accepted = await client.put(
        f"/api/v1/budgets/{budget_id}/status", json={"status": "aceptado"}, headers=_auth(token)
    )
    assert accepted.status_code == 200
    assert accepted.json()["responded_at"] is not None


async def test_dentist_without_treatments_write_cannot_create_plan(client, clinic_with_users, db_session):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    treatment_id = await _create_treatment(client, token)

    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "treatments:write"]
    await db_session.flush()
    await db_session.commit()

    dentist_token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.post(
        f"/api/v1/patients/{patient_id}/treatment-plans",
        json={"items": [{"treatment_id": treatment_id, "price": 10.0}]},
        headers=_auth(dentist_token),
    )
    assert response.status_code == 403
