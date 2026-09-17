async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_list_patient(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")

    created = await client.post(
        "/api/v1/patients",
        json={"first_name": "Ana", "last_name": "Torres", "national_id": "111", "birth_date": "2000-01-15"},
        headers=_auth(token),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["first_name"] == "Ana"
    assert body["age"] is not None

    listing = await client.get("/api/v1/patients", headers=_auth(token))
    assert listing.status_code == 200
    assert any(p["national_id"] == "111" for p in listing.json())


async def test_search_patient_by_name(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    await client.post(
        "/api/v1/patients", json={"first_name": "Beatriz", "last_name": "Luna"}, headers=_auth(token)
    )
    await client.post(
        "/api/v1/patients", json={"first_name": "Jorge", "last_name": "Rios"}, headers=_auth(token)
    )

    response = await client.get("/api/v1/patients", params={"search": "Luna"}, headers=_auth(token))
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["last_name"] == "Luna"


async def test_dentist_without_patients_write_cannot_create(client, clinic_with_users, db_session):
    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "patients:write"]
    await db_session.flush()
    await db_session.commit()

    token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.post(
        "/api/v1/patients", json={"first_name": "X", "last_name": "Y"}, headers=_auth(token)
    )
    assert response.status_code == 403


async def test_deactivated_patient_disappears_from_listing_and_404s(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    created = await client.post(
        "/api/v1/patients", json={"first_name": "Temp", "last_name": "Paciente"}, headers=_auth(token)
    )
    patient_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/patients/{patient_id}", headers=_auth(token))
    assert deleted.status_code == 204

    fetched = await client.get(f"/api/v1/patients/{patient_id}", headers=_auth(token))
    assert fetched.status_code == 404

    listing = await client.get("/api/v1/patients", headers=_auth(token))
    assert all(p["id"] != patient_id for p in listing.json())
