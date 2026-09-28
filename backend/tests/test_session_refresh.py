"""La sesión no debe cerrarse sola cuando dos peticiones renuevan a la vez,
pero tampoco puede revivir después de cerrar sesión o cambiar la contraseña."""

from app.core.config import get_settings

BODY = {"X-Token-Delivery": "body"}


async def _login(client, email="admin@clinicatest.io", password="Admin123!"):
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers=BODY
    )
    return response.json()


async def _refresh(client, token):
    client.cookies.clear()
    return await client.post("/api/v1/auth/refresh", json={"refresh_token": token}, headers=BODY)


async def test_two_refreshes_with_the_same_token_both_succeed(client, clinic_with_users):
    token = (await _login(client))["refresh_token"]
    first = await _refresh(client, token)
    second = await _refresh(client, token)  # otra pestaña, o una petición que ya iba en camino
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["refresh_token"] != token


async def test_old_token_is_refused_after_the_grace_window(client, clinic_with_users, monkeypatch):
    monkeypatch.setattr(get_settings(), "REFRESH_REUSE_GRACE_SECONDS", 0)
    token = (await _login(client))["refresh_token"]
    assert (await _refresh(client, token)).status_code == 200
    assert (await _refresh(client, token)).status_code == 401


async def test_logout_ends_the_grace_window(client, clinic_with_users):
    token = (await _login(client))["refresh_token"]
    renewed = (await _refresh(client, token)).json()["refresh_token"]
    client.cookies.clear()
    await client.post("/api/v1/auth/logout", json={"refresh_token": renewed}, headers=BODY)
    assert (await _refresh(client, token)).status_code == 401
    assert (await _refresh(client, renewed)).status_code == 401


async def test_password_reset_ends_the_grace_window(client, clinic_with_users):
    admin = (await _login(client))["access_token"]
    token = (await _login(client, "dentist@clinicatest.io", "Dentist123!"))["refresh_token"]
    assert (await _refresh(client, token)).status_code == 200
    dentist_id = str(clinic_with_users["dentist"].id)
    await client.put(
        f"/api/v1/users/{dentist_id}", json={"password": "Nueva12345"}, headers={"Authorization": f"Bearer {admin}"}
    )
    assert (await _refresh(client, token)).status_code == 401
