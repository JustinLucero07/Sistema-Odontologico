async def test_login_success_returns_access_token(client, clinic_with_users):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 10
    assert "refresh_token" in response.cookies


async def test_login_wrong_password_rejected(client, clinic_with_users):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email_rejected(client, clinic_with_users):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@clinicatest.io", "password": "whatever123"}
    )
    assert response.status_code == 401


async def test_me_requires_authentication(client, clinic_with_users):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user_and_permissions(client, clinic_with_users):
    login = await client.post(
        "/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"}
    )
    token = login.json()["access_token"]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@clinicatest.io"
    assert "users:manage" in body["permissions"]


async def test_refresh_rotates_token_and_old_cookie_is_invalid(client, clinic_with_users):
    login = await client.post(
        "/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"}
    )
    first_refresh_cookie = login.cookies["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.cookies["refresh_token"] != first_refresh_cookie

    client.cookies.set("refresh_token", first_refresh_cookie)
    reused = await client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401


async def test_logout_revokes_refresh_token(client, clinic_with_users):
    await client.post("/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"})
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    after_logout = await client.post("/api/v1/auth/refresh")
    assert after_logout.status_code == 401
