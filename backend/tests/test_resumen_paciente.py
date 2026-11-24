import httpx
import pytest

from app.modules.ai_assist import briefing
from app.shared import ai as ai_mod


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _paciente(client, h):
    pid = (await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Mora"}, headers=h)).json()["id"]
    await client.post(
        f"/api/v1/patients/{pid}/medical-history",
        json={"allergies": "Penicilina", "medications": "ninguna", "medical_conditions": "Hipertensión"},
        headers=h,
    )
    await client.post(f"/api/v1/patients/{pid}/charges", json={"description": "Resina", "amount": "30"}, headers=h)
    return pid


async def test_datos_clave(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    r = await client.get(f"/api/v1/patients/{pid}/briefing", headers=h)
    assert r.status_code == 200, r.text
    datos = {d["codigo"]: d for d in r.json()["datos"]}
    assert datos["alergias"]["texto"] == "Alergias: Penicilina" and datos["alergias"]["tono"] == "alerta"
    assert "Hipertensión" in datos["condiciones"]["texto"]
    assert "medicacion" not in datos  # «ninguna» no es un dato
    assert datos["saldo"]["texto"].startswith("Debe $30,00")
    assert datos["cita"]["texto"] == "Sin próxima cita agendada"
    assert r.json()["ia_disponible"] is False


async def test_sin_permiso_de_pagos_no_ve_el_saldo(client):
    odonto = await _h(client, "dentist@clinicatest.io", "Dentist123!")
    pid = await _paciente(client, await _h(client))
    codigos = {d["codigo"] for d in (await client.get(f"/api/v1/patients/{pid}/briefing", headers=odonto)).json()["datos"]}
    assert "saldo" not in codigos and "alergias" in codigos


async def test_sin_ia_configurada(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    assert (await client.post(f"/api/v1/patients/{pid}/briefing/ai", headers=h)).status_code == 503


class _Falso(ai_mod.AiProvider):
    name = "falso"

    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.recibido = None

    @property
    def is_available(self):
        return True

    async def complete(self, system, user):
        self.recibido = user
        return self.respuesta


async def test_resumen_con_ia_sin_dinero(client, monkeypatch):
    h = await _h(client)
    pid = await _paciente(client, h)
    falso = _Falso("Paciente con alergia a la penicilina e hipertensión registradas. No tiene cita agendada.")
    monkeypatch.setattr(briefing, "get_ai", lambda: falso)
    r = await client.post(f"/api/v1/patients/{pid}/briefing/ai", headers=h)
    assert r.status_code == 200, r.text
    assert "penicilina" in r.json()["texto"]
    assert "Penicilina" in falso.recibido
    # El saldo nunca llega a la IA.
    assert "Debe" not in falso.recibido and "$" not in falso.recibido

    # Si la IA menciona dinero igual, el texto se descarta.
    monkeypatch.setattr(briefing, "get_ai", lambda: _Falso("Debe $30 de una resina."))
    assert (await client.post(f"/api/v1/patients/{pid}/briefing/ai", headers=h)).status_code == 422


async def test_peticion_a_claude(monkeypatch):
    enviado = {}

    async def falso_post(self, url, json=None, headers=None):
        enviado.update(url=url, json=json, headers=headers)
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "Hola"}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", falso_post)
    p = ai_mod.AnthropicProvider("k", "claude-opus-5-5", 4000, "low")
    assert await p.complete("sistema", "usuario") == "Hola"
    assert enviado["json"]["model"] == "claude-opus-5-5"
    assert enviado["json"]["output_config"] == {"effort": "low"}
    assert enviado["json"]["fallbacks"] == "default"
    assert enviado["headers"]["anthropic-version"] == "2026-10-21"
    assert "temperature" not in enviado["json"]


async def test_rechazo_de_claude(monkeypatch):
    async def falso_post(self, url, json=None, headers=None):
        return httpx.Response(200, json={"stop_reason": "refusal", "content": []})

    monkeypatch.setattr(httpx.AsyncClient, "post", falso_post)
    with pytest.raises(ai_mod.AiUnavailable):
        await ai_mod.AnthropicProvider("k", "claude-opus-5-5", 4000).complete("s", "u")


