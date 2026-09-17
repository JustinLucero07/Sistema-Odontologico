async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client, token) -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": "Sofía", "last_name": "Vega"}, headers=_auth(token)
    )
    return created.json()["id"]


async def test_no_odontogram_yet_returns_null(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=_auth(token))
    assert response.status_code == 200
    assert response.json() is None


async def test_first_snapshot_is_type_initial(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontogram",
        json={"conditions": [{"fdi_number": "16", "surface": "oclusal", "condition": "caries"}]},
        headers=_auth(token),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["type"] == "initial"
    assert body["previous_odontogram_id"] is None
    assert len(body["conditions"]) == 1
    assert body["conditions"][0]["fdi_number"] == "16"


async def test_second_snapshot_links_to_first_and_never_overwrites_it(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/odontogram",
        json={"conditions": [{"fdi_number": "16", "surface": "oclusal", "condition": "caries"}]},
        headers=_auth(token),
    )
    first_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/patients/{patient_id}/odontogram",
        json={"conditions": [
            {"fdi_number": "16", "surface": "oclusal", "condition": "restauracion"},
            {"fdi_number": "26", "surface": "whole", "condition": "ausente"},
        ]},
        headers=_auth(token),
    )
    assert second.status_code == 201
    second_body = second.json()
    assert second_body["type"] == "followup"
    assert second_body["previous_odontogram_id"] == first_id

    # the latest snapshot reflects only the new state
    latest = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=_auth(token))
    assert latest.json()["id"] == second_body["id"]
    assert len(latest.json()["conditions"]) == 2

    # but the first snapshot is untouched — nothing was overwritten
    old = await client.get(f"/api/v1/patients/{patient_id}/odontogram/{first_id}", headers=_auth(token))
    assert old.status_code == 200
    assert old.json()["conditions"] == [
        {"id": old.json()["conditions"][0]["id"], "fdi_number": "16", "surface": "oclusal",
         "condition": "caries", "notes": None}
    ]

    versions = await client.get(f"/api/v1/patients/{patient_id}/odontogram/versions", headers=_auth(token))
    assert versions.status_code == 200
    assert len(versions.json()) == 2


async def test_invalid_fdi_number_rejected(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/odontogram",
        json={"conditions": [{"fdi_number": "99", "surface": "oclusal", "condition": "caries"}]},
        headers=_auth(token),
    )
    assert response.status_code == 422


async def test_dentist_without_write_permission_gets_403(client, clinic_with_users, db_session):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "odontogram:write"]
    await db_session.flush()
    await db_session.commit()

    dentist_token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.post(
        f"/api/v1/patients/{patient_id}/odontogram",
        json={"conditions": []},
        headers=_auth(dentist_token),
    )
    assert response.status_code == 403
