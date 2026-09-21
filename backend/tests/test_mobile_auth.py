"""Entrega del token de refresco a clientes sin cookies.

Una app móvil no tiene almacén de cookies. Estas pruebas comprueban que puede
autenticarse, y —más importante— que darle esa vía no ha debilitado al
navegador: su token sigue viviendo solo en una cookie httpOnly.
"""

MOBILE = {"X-Token-Delivery": "body"}


async def _login(client, headers=None):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clinicatest.io", "password": "Admin123!"},
        headers=headers,
    )


async def test_a_browser_never_receives_the_refresh_token(client, clinic_with_users):
    """Sin la cabecera, el token solo va en la cookie httpOnly: si JavaScript
    pudiera leerlo, la cookie no serviría de nada."""
    response = await _login(client)
    assert response.status_code == 200
    assert response.json()["refresh_token"] is None
    assert "refresh_token" in response.cookies


async def test_a_mobile_client_receives_it_in_the_body(client, clinic_with_users):
    response = await _login(client, MOBILE)
    assert response.status_code == 200
    token = response.json()["refresh_token"]
    assert token and len(token) > 40


async def test_the_body_token_can_refresh_a_session(client, clinic_with_users):
    token = (await _login(client, MOBILE)).json()["refresh_token"]
    client.cookies.clear()  # como un móvil: sin cookies de por medio

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}, headers=MOBILE
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    # El token rota, igual que en el navegador.
    assert refreshed.json()["refresh_token"] != token


async def test_a_rotated_token_cannot_be_reused(client, clinic_with_users):
    """La rotación solo protege si el token viejo muere al usarse."""
    token = (await _login(client, MOBILE)).json()["refresh_token"]
    client.cookies.clear()

    first = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}, headers=MOBILE
    )
    assert first.status_code == 200

    # El endpoint también deja la cookie puesta, y la cookie manda sobre el
    # cuerpo. Sin limpiarla, el reintento usaría la cookie NUEVA (que sí vale)
    # y la prueba no estaría comprobando nada.
    client.cookies.clear()
    replay = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}, headers=MOBILE
    )
    assert replay.status_code == 401


async def test_refresh_without_any_token_is_refused(client, clinic_with_users):
    client.cookies.clear()
    response = await client.post("/api/v1/auth/refresh", json={}, headers=MOBILE)
    assert response.status_code == 401


async def test_the_cookie_wins_over_a_body_token(client, clinic_with_users):
    """Un navegador no debe poder sortear su propia cookie mandando otro token
    en el cuerpo."""
    await _login(client)  # deja la cookie puesta
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "token-inventado"}
    )
    assert response.status_code == 200  # usó la cookie, ignoró el cuerpo
