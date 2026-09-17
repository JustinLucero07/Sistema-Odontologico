async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_admin_can_list_users(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    response = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


async def test_dentist_without_users_manage_gets_403(client, clinic_with_users):
    token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "No tiene el permiso requerido: users:manage"


async def test_dentist_can_read_professionals(client, clinic_with_users):
    token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.get("/api/v1/professionals", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


async def test_endpoint_without_token_is_401(client, clinic_with_users):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401


async def test_revoking_role_permission_takes_effect_on_next_request(client, clinic_with_users, db_session):
    """Permissions are re-read from the database on every request, not trusted
    from the access token — see app.core.deps.get_current_user."""
    token = await _login(client, "dentist@clinicatest.io", "Dentist123!")

    ok = await client.get("/api/v1/professionals", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "appointments:read"]
    await db_session.flush()
    await db_session.commit()

    blocked = await client.get("/api/v1/professionals", headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 403
