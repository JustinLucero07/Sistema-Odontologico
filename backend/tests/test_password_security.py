"""Contraseñas: política, cambio propio y contraseña temporal."""

import pytest

from app.core.password_policy import problems


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client, email="admin@clinicatest.io", password="Admin123!"):
    return await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers={"X-Token-Delivery": "body"}
    )


@pytest.mark.parametrize(
    "password, ok",
    [
        ("Molar-2026-azul", True),
        ("corta1", False),
        ("sololetrasss", False),
        ("1234567890", False),
        ("password123", False),
        ("lucia2026x", False),  # contiene el nombre
    ],
)
def test_policy(password, ok):
    assert (problems(password, email="lucia.arce@clinica.ec", names=("Lucía", "Arce")) == []) is ok


async def test_admin_set_password_is_temporary_and_must_be_changed(client, clinic_with_users):
    admin = _auth((await _login(client)).json()["access_token"])
    created = await client.post(
        "/api/v1/users",
        json={"email": "nueva@clinicatest.io", "password": "Temporal-4821", "first_name": "Rosa", "last_name": "Vera", "role_ids": []},
        headers=admin,
    )
    assert created.status_code == 201
    weak = await client.post(
        "/api/v1/users",
        json={"email": "otra@clinicatest.io", "password": "12345678", "first_name": "Ana", "last_name": "Paz", "role_ids": []},
        headers=admin,
    )
    assert weak.status_code == 422

    token = (await _login(client, "nueva@clinicatest.io", "Temporal-4821")).json()["access_token"]
    assert (await client.get("/api/v1/auth/me", headers=_auth(token))).json()["must_change_password"] is True


async def test_user_changes_own_password_and_other_sessions_close(client, clinic_with_users):
    other_device = (await _login(client, "dentist@clinicatest.io", "Dentist123!")).json()["refresh_token"]
    here = (await _login(client, "dentist@clinicatest.io", "Dentist123!")).json()
    h = {**_auth(here["access_token"]), "X-Token-Delivery": "body"}

    wrong = await client.post(
        "/api/v1/auth/change-password", json={"current_password": "no-es", "new_password": "Molar-2026-azul"}, headers=h
    )
    assert wrong.status_code == 400
    same = await client.post(
        "/api/v1/auth/change-password", json={"current_password": "Dentist123!", "new_password": "Dentist123!"}, headers=h
    )
    assert same.status_code == 422
    weak = await client.post(
        "/api/v1/auth/change-password", json={"current_password": "Dentist123!", "new_password": "abc"}, headers=h
    )
    assert weak.status_code == 422

    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Dentist123!", "new_password": "Molar-2026-azul"},
        headers=h,
    )
    assert changed.status_code == 200
    new_refresh = changed.json()["refresh_token"]

    assert (await _login(client, "dentist@clinicatest.io", "Dentist123!")).status_code == 401
    assert (await _login(client, "dentist@clinicatest.io", "Molar-2026-azul")).status_code == 200
    me = await client.get("/api/v1/auth/me", headers=_auth(changed.json()["access_token"]))
    assert me.json()["must_change_password"] is False

    # El otro dispositivo queda fuera; esta sesión sigue.
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": other_device}, headers={"X-Token-Delivery": "body"})).status_code == 401
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh}, headers={"X-Token-Delivery": "body"})).status_code == 200
