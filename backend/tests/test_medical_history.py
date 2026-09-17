async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client, token) -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": "Luis", "last_name": "Andrade"}, headers=_auth(token)
    )
    return created.json()["id"]


async def test_no_history_yet_returns_null(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.get(f"/api/v1/patients/{patient_id}/medical-history", headers=_auth(token))
    assert response.status_code == 200
    assert response.json() is None


async def test_creating_a_new_version_never_overwrites_the_previous_one(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/medical-history",
        json={"allergies": "Ninguna conocida", "chief_complaint": "Dolor en muela"},
        headers=_auth(token),
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/patients/{patient_id}/medical-history",
        json={"allergies": "Penicilina (descubierta después)", "chief_complaint": "Control de rutina"},
        headers=_auth(token),
    )
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]

    latest = await client.get(f"/api/v1/patients/{patient_id}/medical-history", headers=_auth(token))
    assert latest.json()["allergies"] == "Penicilina (descubierta después)"

    versions = await client.get(
        f"/api/v1/patients/{patient_id}/medical-history/versions", headers=_auth(token)
    )
    assert versions.status_code == 200
    version_bodies = versions.json()
    assert len(version_bodies) == 2
    # the original version's data must still be intact, not overwritten
    original = next(v for v in version_bodies if v["id"] == first.json()["id"])
    assert original["allergies"] == "Ninguna conocida"


async def test_role_without_write_permission_cannot_create_a_version(client, clinic_with_users, db_session):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "medical_history:write"]
    await db_session.flush()
    await db_session.commit()

    dentist_token = await _login(client, "dentist@clinicatest.io", "Dentist123!")

    read_response = await client.get(
        f"/api/v1/patients/{patient_id}/medical-history", headers=_auth(dentist_token)
    )
    assert read_response.status_code == 200

    write_response = await client.post(
        f"/api/v1/patients/{patient_id}/medical-history",
        json={"chief_complaint": "intento no autorizado"},
        headers=_auth(dentist_token),
    )
    assert write_response.status_code == 403
