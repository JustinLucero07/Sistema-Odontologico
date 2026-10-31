"""Reenvíos de la app sin conexión: la misma Idempotency-Key no duplica."""

import uuid

import pytest


def _redis_disponible() -> bool:
    try:
        import redis

        from app.core.config import get_settings

        redis.Redis.from_url(get_settings().REDIS_URL, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_disponible(), reason="Redis no disponible")


async def _login(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_mismo_cambio_reenviado_no_se_duplica(client, clinic_with_users):
    h = await _login(client)
    llave = str(uuid.uuid4())
    datos = {"first_name": "Rosa", "last_name": "Reenvío"}
    r1 = await client.post("/api/v1/patients", json=datos, headers={**h, "Idempotency-Key": llave})
    r2 = await client.post("/api/v1/patients", json=datos, headers={**h, "Idempotency-Key": llave})
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.headers.get("idempotent-replay") == "true"
    lista = (await client.get("/api/v1/patients", params={"search": "Reenvío"}, headers=h)).json()
    assert len([p for p in (lista if isinstance(lista, list) else lista["items"]) if p["last_name"] == "Reenvío"]) == 1

    # Otra llave sí crea otro.
    r3 = await client.post("/api/v1/patients", json=datos, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r3.json()["id"] != r1.json()["id"]


async def test_la_llave_de_otro_usuario_no_devuelve_su_respuesta(client, clinic_with_users):
    llave = str(uuid.uuid4())
    ha = await _login(client)
    r1 = await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Privada"}, headers={**ha, "Idempotency-Key": llave})
    hd = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    r2 = await client.post("/api/v1/patients", json={"first_name": "Otro", "last_name": "Usuario"}, headers={**hd, "Idempotency-Key": llave})
    assert r2.status_code == 201 and r2.json()["id"] != r1.json()["id"]
    assert r2.headers.get("idempotent-replay") is None
