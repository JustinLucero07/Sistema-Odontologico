"""Protección de datos: lo que la ley pide poder demostrar.

- Que al paciente se le informó (aviso de privacidad), con qué versión y cómo.
- Que sus autorizaciones se pueden retirar, y que retirarlas tiene efecto.
- Que puede obtener una copia de todos sus datos.
- Quién abrió su historia.
- Que el personal aceptó guardar confidencialidad.
"""

from datetime import date


async def _login(client, email="admin@clinicatest.io", password="Admin123!"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _prescriber(client, headers) -> str:
    """Toda receta necesita un profesional que la firme."""
    response = await client.post(
        "/api/v1/professionals", json={"first_name": "Ana", "last_name": "Molina"}, headers=headers
    )
    return response.json()["id"]


async def _patient(client, h, **extra) -> str:
    created = await client.post(
        "/api/v1/patients",
        json={"first_name": "Lucía", "last_name": "Arce", "whatsapp": "+593999000111", **extra},
        headers=h,
    )
    return created.json()["id"]


async def test_notice_and_communications_are_recorded_with_version(client, clinic_with_users):
    h = _auth(await _login(client))
    patient_id = await _patient(client, h)

    empty = (await client.get(f"/api/v1/patients/{patient_id}/privacy", headers=h)).json()
    assert empty["privacy_notice"] is None
    assert empty["communications"] is None

    notice = await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents",
        json={"kind": "aviso_privacidad", "method": "firma_presencial"},
        headers=h,
    )
    assert notice.status_code == 201
    await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents",
        json={"kind": "comunicaciones", "granted": True, "method": "verbal"},
        headers=h,
    )

    status = (await client.get(f"/api/v1/patients/{patient_id}/privacy", headers=h)).json()
    assert status["privacy_notice"]["policy_version"] == status["current_policy_version"]
    assert status["privacy_notice"]["recorded_by_name"] == "Admin Test"
    assert status["communications"]["granted"] is True
    assert status["notice_outdated"] is False


async def test_notice_cannot_be_withdrawn(client, clinic_with_users):
    h = _auth(await _login(client))
    patient_id = await _patient(client, h)
    response = await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents",
        json={"kind": "aviso_privacidad", "granted": False},
        headers=h,
    )
    assert response.status_code == 400


async def test_minors_need_a_legal_representative(client, clinic_with_users):
    h = _auth(await _login(client))
    birth = date(date.today().year - 10, 1, 1).isoformat()
    patient_id = await _patient(client, h, birth_date=birth)

    without = await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents", json={"kind": "aviso_privacidad"}, headers=h
    )
    assert without.status_code == 422

    with_rep = await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents",
        json={"kind": "aviso_privacidad", "signed_by_name": "Rosa Arce (madre)"},
        headers=h,
    )
    assert with_rep.status_code == 201
    assert with_rep.json()["signed_by_name"] == "Rosa Arce (madre)"


async def test_withdrawn_communications_block_messages(client, clinic_with_users):
    h = _auth(await _login(client))
    patient_id = await _patient(client, h)

    sent = await client.post(
        "/api/v1/messaging/messages",
        json={"patient_id": patient_id, "channel": "whatsapp", "body": "Recordatorio"},
        headers=h,
    )
    assert sent.status_code == 201

    await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents",
        json={"kind": "comunicaciones", "granted": False, "method": "verbal"},
        headers=h,
    )
    blocked = await client.post(
        "/api/v1/messaging/messages",
        json={"patient_id": patient_id, "channel": "whatsapp", "body": "Recordatorio"},
        headers=h,
    )
    assert blocked.status_code == 409
    assert "retiró" in blocked.json()["detail"]

    # Volver a autorizar reabre el canal: la última decisión es la que vale.
    await client.post(
        f"/api/v1/patients/{patient_id}/privacy/consents",
        json={"kind": "comunicaciones", "granted": True, "method": "verbal"},
        headers=h,
    )
    again = await client.post(
        "/api/v1/messaging/messages",
        json={"patient_id": patient_id, "channel": "whatsapp", "body": "Recordatorio"},
        headers=h,
    )
    assert again.status_code == 201

    history = (await client.get(f"/api/v1/patients/{patient_id}/privacy", headers=h)).json()["history"]
    assert [c["granted"] for c in history if c["kind"] == "comunicaciones"] == [True, False]


async def test_export_contains_everything_and_nothing_internal(client, clinic_with_users):
    h = _auth(await _login(client))
    patient_id = await _patient(client, h)
    await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses", json={"description": "Caries 36", "fdi_number": "36"}, headers=h
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions",
        json={"professional_id": await _prescriber(client, h), "items": [{"medication": "Ibuprofeno 400 mg"}]},
        headers=h,
    )
    await client.post(f"/api/v1/patients/{patient_id}/portal", json={}, headers=h)

    response = await client.get(f"/api/v1/patients/{patient_id}/privacy/export", headers=h)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()

    assert data["patient"]["first_name"] == "Lucía"
    assert data["records"]["diagnoses"][0]["description"] == "Caries 36"
    # Las tablas hijas llegan aunque no tengan patient_id.
    assert data["records"]["prescription_items"][0]["medication"] == "Ibuprofeno 400 mg"
    text = response.text
    assert "token_hash" not in text
    assert "clinic_id" not in text


async def test_export_is_restricted_and_logged(client, clinic_with_users):
    admin = _auth(await _login(client))
    patient_id = await _patient(client, admin)

    dentist = _auth(await _login(client, "dentist@clinicatest.io", "Dentist123!"))
    assert (await client.get(f"/api/v1/patients/{patient_id}/privacy/export", headers=dentist)).status_code == 403

    await client.get(f"/api/v1/patients/{patient_id}/privacy/export", headers=admin)
    log = (await client.get(f"/api/v1/patients/{patient_id}/privacy/access-log", headers=admin)).json()
    assert any(entry["action"] == "export" for entry in log)


async def test_opening_a_record_is_logged_once_per_visit(client, clinic_with_users):
    admin = _auth(await _login(client))
    patient_id = await _patient(client, admin)
    dentist = _auth(await _login(client, "dentist@clinicatest.io", "Dentist123!"))

    for _ in range(3):
        await client.get(f"/api/v1/patients/{patient_id}", headers=dentist)

    log = (await client.get(f"/api/v1/patients/{patient_id}/privacy/access-log", headers=admin)).json()
    views = [e for e in log if e["action"] == "view" and e["user_name"] == "Dentist Test"]
    # Tres recargas seguidas son una sola visita.
    assert len(views) == 1


async def test_access_log_needs_audit_permission(client, clinic_with_users):
    admin = _auth(await _login(client))
    patient_id = await _patient(client, admin)
    dentist = _auth(await _login(client, "dentist@clinicatest.io", "Dentist123!"))
    assert (
        await client.get(f"/api/v1/patients/{patient_id}/privacy/access-log", headers=dentist)
    ).status_code == 403


async def test_staff_must_accept_confidentiality(client, clinic_with_users):
    h = _auth(await _login(client, "dentist@clinicatest.io", "Dentist123!"))
    assert (await client.get("/api/v1/auth/me", headers=h)).json()["confidentiality_required"] is True

    assert (await client.post("/api/v1/auth/confidentiality", headers=h)).status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=h)).json()["confidentiality_required"] is False


async def test_controller_identity_is_available_to_staff(client, clinic_with_users):
    h = _auth(await _login(client, "dentist@clinicatest.io", "Dentist123!"))
    body = (await client.get("/api/v1/legal/controller", headers=h)).json()
    assert body["name"] == "Clínica Test"
    assert body["privacy_policy_version"]
