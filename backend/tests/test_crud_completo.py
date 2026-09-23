"""Editar y dar de baja lo que antes solo se podía crear.

Dos reglas atraviesan todo el archivo: lo administrativo (catálogos, personas,
proveedores) se edita y se desactiva; lo clínico (diagnósticos, recetas) nunca
se borra, se anula con un motivo y sigue a la vista.
"""


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response


async def _token(client, email="admin@clinicatest.io", password="Admin123!"):
    return (await _login(client, email, password)).json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _prescriber(client, headers) -> str:
    """Toda receta necesita un profesional que la firme."""
    response = await client.post(
        "/api/v1/professionals", json={"first_name": "Ana", "last_name": "Molina"}, headers=headers
    )
    return response.json()["id"]


async def _patient(client, token) -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": "Lucía", "last_name": "Arce"}, headers=_auth(token)
    )
    return created.json()["id"]


# ---- Especialidades y profesionales -------------------------------------


async def test_specialty_is_renamed_and_only_deleted_when_unused(client, clinic_with_users):
    token = await _token(client)
    h = _auth(token)
    spec = (await client.post("/api/v1/specialties", json={"name": "Ortodonsia"}, headers=h)).json()

    renamed = await client.put(f"/api/v1/specialties/{spec['id']}", json={"name": "Ortodoncia"}, headers=h)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Ortodoncia"

    prof = (
        await client.post(
            "/api/v1/professionals",
            json={"first_name": "Ana", "last_name": "Ruiz", "specialty_id": spec["id"]},
            headers=h,
        )
    ).json()
    blocked = await client.delete(f"/api/v1/specialties/{spec['id']}", headers=h)
    assert blocked.status_code == 409

    await client.put(f"/api/v1/professionals/{prof['id']}", json={"specialty_id": None}, headers=h)
    assert (await client.delete(f"/api/v1/specialties/{spec['id']}", headers=h)).status_code == 204


async def test_professional_is_edited_and_deactivated(client, clinic_with_users):
    h = _auth(await _token(client))
    prof = (
        await client.post("/api/v1/professionals", json={"first_name": "Ana", "last_name": "Ruiz"}, headers=h)
    ).json()
    updated = await client.put(
        f"/api/v1/professionals/{prof['id']}",
        json={"license_number": "MSP-123", "color_hex": "#B9832F", "is_active": False},
        headers=h,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["license_number"] == "MSP-123"
    assert body["is_active"] is False


# ---- Usuarios y roles ---------------------------------------------------


async def test_password_reset_logs_the_user_out_everywhere(client, clinic_with_users):
    admin = _auth(await _token(client))
    dentist_login = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    refresh = dentist_login.cookies.get("refresh_token") or dentist_login.json().get("refresh_token")
    dentist_id = str(clinic_with_users["dentist"].id)

    reset = await client.put(f"/api/v1/users/{dentist_id}", json={"password": "Nueva12345"}, headers=admin)
    assert reset.status_code == 200

    # La contraseña vieja ya no entra y la nueva sí.
    assert (await _login(client, "dentist@clinicatest.io", "Dentist123!")).status_code == 401
    assert (await _login(client, "dentist@clinicatest.io", "Nueva12345")).status_code == 200

    # La sesión que tenía abierta antes del cambio no se puede renovar.
    if refresh:
        client.cookies.clear()
        renewed = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
            headers={"X-Token-Delivery": "body"},
        )
        assert renewed.status_code == 401


async def test_password_reset_requires_minimum_length(client, clinic_with_users):
    admin = _auth(await _token(client))
    dentist_id = str(clinic_with_users["dentist"].id)
    short = await client.put(f"/api/v1/users/{dentist_id}", json={"password": "corta"}, headers=admin)
    assert short.status_code == 422


async def test_admin_cannot_deactivate_themselves(client, clinic_with_users):
    admin = _auth(await _token(client))
    admin_id = str(clinic_with_users["admin"].id)
    assert (await client.delete(f"/api/v1/users/{admin_id}", headers=admin)).status_code == 400
    assert (
        await client.put(f"/api/v1/users/{admin_id}", json={"is_active": False}, headers=admin)
    ).status_code == 400


async def test_user_is_edited_and_reactivated(client, clinic_with_users):
    admin = _auth(await _token(client))
    dentist_id = str(clinic_with_users["dentist"].id)
    assert (await client.delete(f"/api/v1/users/{dentist_id}", headers=admin)).status_code == 204
    back = await client.put(
        f"/api/v1/users/{dentist_id}", json={"is_active": True, "first_name": "Diana"}, headers=admin
    )
    assert back.status_code == 200
    assert back.json()["is_active"] is True
    assert back.json()["first_name"] == "Diana"


async def test_role_in_use_cannot_be_deleted(client, clinic_with_users):
    admin = _auth(await _token(client))
    role = (
        await client.post(
            "/api/v1/roles", json={"name": "Higienista", "permission_codes": ["patients:read"]}, headers=admin
        )
    ).json()
    dentist_id = str(clinic_with_users["dentist"].id)
    await client.put(f"/api/v1/users/{dentist_id}", json={"role_ids": [role["id"]]}, headers=admin)

    assert (await client.delete(f"/api/v1/roles/{role['id']}", headers=admin)).status_code == 409

    await client.put(f"/api/v1/users/{dentist_id}", json={"role_ids": []}, headers=admin)
    assert (await client.delete(f"/api/v1/roles/{role['id']}", headers=admin)).status_code == 204


# ---- Inventario y laboratorio -------------------------------------------


async def test_supplier_is_edited_and_deactivated(client, clinic_with_users):
    h = _auth(await _token(client))
    supplier = (await client.post("/api/v1/inventory/suppliers", json={"name": "Dental Sur"}, headers=h)).json()
    updated = await client.put(
        f"/api/v1/inventory/suppliers/{supplier['id']}",
        json={"name": "Dental Sur S.A.", "phone": "0999", "is_active": False},
        headers=h,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Dental Sur S.A."
    assert updated.json()["is_active"] is False


async def test_lab_order_details_are_editable_until_closed(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    lab = (await client.post("/api/v1/laboratory/laboratories", json={"name": "Lab Andes"}, headers=h)).json()
    lab2 = (await client.post("/api/v1/laboratory/laboratories", json={"name": "Lab Costa"}, headers=h)).json()

    renamed = await client.put(
        f"/api/v1/laboratory/laboratories/{lab['id']}",
        json={"name": "Laboratorio Andes", "default_turnaround_days": 7},
        headers=h,
    )
    assert renamed.status_code == 200
    assert renamed.json()["default_turnaround_days"] == 7

    order = (
        await client.post(
            "/api/v1/laboratory/orders",
            json={"patient_id": patient_id, "laboratory_id": lab["id"], "work_type": "corona", "description": "Corona 16"},
            headers=h,
        )
    ).json()
    edit = {
        "laboratory_id": lab2["id"], "work_type": "corona", "description": "Corona de zirconio 16",
        "fdi_numbers": ["16"], "shade": "A2", "cost": "120.00",
    }
    edited = await client.put(f"/api/v1/laboratory/orders/{order['id']}", json=edit, headers=h)
    assert edited.status_code == 200
    body = edited.json()
    assert body["description"] == "Corona de zirconio 16"
    assert body["laboratory_name"] == "Lab Costa"
    # Editar no cambia el estado ni deja rastro de estado nuevo.
    assert body["status"] == order["status"]
    assert len(body["events"]) == len(order["events"])

    await client.put(f"/api/v1/laboratory/orders/{order['id']}/status", json={"status": "cancelado"}, headers=h)
    closed = await client.put(f"/api/v1/laboratory/orders/{order['id']}", json=edit, headers=h)
    assert closed.status_code == 409


# ---- Planes y consentimientos -------------------------------------------


async def test_plan_title_is_editable(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    plan = (
        await client.post(f"/api/v1/patients/{patient_id}/treatment-plans", json={"title": "Plan"}, headers=h)
    ).json()
    updated = await client.put(
        f"/api/v1/treatment-plans/{plan['id']}", json={"title": "Rehabilitación superior", "notes": "Fase 1"}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Rehabilitación superior"


async def test_retiring_a_consent_template_keeps_issued_consents_intact(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    template = (
        await client.post(
            "/api/v1/consents/templates", json={"name": "Exodoncia", "body": "Texto original"}, headers=h
        )
    ).json()
    consent = (
        await client.post(f"/api/v1/patients/{patient_id}/consents", json={"template_id": template["id"]}, headers=h)
    ).json()

    changed = await client.put(
        f"/api/v1/consents/templates/{template['id']}",
        json={"name": "Exodoncia", "body": "Texto nuevo", "is_active": False},
        headers=h,
    )
    assert changed.status_code == 200

    active = (await client.get("/api/v1/consents/templates", headers=h)).json()
    assert template["id"] not in [t["id"] for t in active]
    everything = (await client.get("/api/v1/consents/templates?include_inactive=true", headers=h)).json()
    assert template["id"] in [t["id"] for t in everything]

    issued = (await client.get(f"/api/v1/patients/{patient_id}/consents", headers=h)).json()
    assert next(c for c in issued if c["id"] == consent["id"])["body"] == "Texto original"


# ---- Registros clínicos: se anulan, no se borran --------------------------


async def test_diagnosis_is_voided_with_reason_and_stays_visible(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    dx = (
        await client.post(
            f"/api/v1/patients/{patient_id}/diagnoses", json={"description": "Caries 36", "fdi_number": "36"}, headers=h
        )
    ).json()

    no_reason = await client.post(f"/api/v1/patients/{patient_id}/diagnoses/{dx['id']}/void", json={"reason": ""}, headers=h)
    assert no_reason.status_code == 422

    voided = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses/{dx['id']}/void", json={"reason": "Pieza equivocada"}, headers=h
    )
    assert voided.status_code == 200
    assert voided.json()["voided_at"] is not None

    again = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses/{dx['id']}/void", json={"reason": "Otra vez"}, headers=h
    )
    assert again.status_code == 409

    listed = (await client.get(f"/api/v1/patients/{patient_id}/diagnoses", headers=h)).json()
    kept = next(d for d in listed if d["id"] == dx["id"])
    assert kept["void_reason"] == "Pieza equivocada"


async def test_prescription_is_voided_not_deleted(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    rx = (
        await client.post(
            f"/api/v1/patients/{patient_id}/prescriptions",
            json={"professional_id": await _prescriber(client, h), "items": [{"medication": "Ibuprofeno 400 mg"}]},
            headers=h,
        )
    ).json()
    voided = await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions/{rx['id']}/void", json={"reason": "Dosis mal escrita"}, headers=h
    )
    assert voided.status_code == 200
    assert voided.json()["items"][0]["medication"] == "Ibuprofeno 400 mg"

    listed = (await client.get(f"/api/v1/patients/{patient_id}/prescriptions", headers=h)).json()
    assert len(listed) == 1 and listed[0]["voided_at"] is not None


async def test_voiding_needs_write_permission(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    dx = (
        await client.post(f"/api/v1/patients/{patient_id}/diagnoses", json={"description": "Caries"}, headers=h)
    ).json()
    # Contabilidad no toca registros clínicos.
    role = (
        await client.post("/api/v1/roles", json={"name": "Solo lectura", "permission_codes": ["diagnoses:read"]}, headers=h)
    ).json()
    await client.put(f"/api/v1/users/{clinic_with_users['dentist'].id}", json={"role_ids": [role["id"]]}, headers=h)
    reader = _auth(await _token(client, "dentist@clinicatest.io", "Dentist123!"))
    denied = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses/{dx['id']}/void", json={"reason": "No debería"}, headers=reader
    )
    assert denied.status_code == 403


# ---- Sedes y consultorios -----------------------------------------------


async def test_branch_with_rooms_is_not_deleted_and_rooms_are_editable(client, clinic_with_users):
    h = _auth(await _token(client))
    branch = (await client.post("/api/v1/clinics/branches", json={"name": "Matriz"}, headers=h)).json()
    room = (
        await client.post("/api/v1/clinics/operatories", json={"branch_id": branch["id"], "name": "Sillón 1"}, headers=h)
    ).json()

    assert (await client.delete(f"/api/v1/clinics/branches/{branch['id']}", headers=h)).status_code == 409

    renamed = await client.put(
        f"/api/v1/clinics/operatories/{room['id']}", json={"name": "Consultorio A", "is_active": False}, headers=h
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Consultorio A"
    assert renamed.json()["is_active"] is False

    assert (await client.delete(f"/api/v1/clinics/operatories/{room['id']}", headers=h)).status_code == 204
    assert (await client.delete(f"/api/v1/clinics/branches/{branch['id']}", headers=h)).status_code == 204


# ---- Radiografías, documentos y consentimientos ---------------------------


def _png() -> bytes:
    from tests.test_phase7 import _png_bytes

    return _png_bytes()


async def test_image_metadata_is_editable_and_archive_is_reversible(client, clinic_with_users, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "STORAGE_LOCAL_PATH", str(tmp_path))
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    image = (
        await client.post(
            f"/api/v1/patients/{patient_id}/images",
            files={"file": ("rx.png", _png(), "image/png")},
            data={"title": "Periapical", "image_type": "periapical"},
            headers=h,
        )
    ).json()

    edited = await client.put(
        f"/api/v1/images/{image['id']}",
        json={"title": "Periapical 16-17", "image_type": "periapical", "fdi_numbers": ["16", "17"]},
        headers=h,
    )
    assert edited.status_code == 200
    assert edited.json()["fdi_numbers"] == ["16", "17"]

    bad = await client.put(
        f"/api/v1/images/{image['id']}", json={"title": "X", "image_type": "periapical", "fdi_numbers": ["99"]}, headers=h
    )
    assert bad.status_code == 400

    await client.post(f"/api/v1/images/{image['id']}/archive", json={"reason": "Paciente equivocado"}, headers=h)
    restored = await client.post(f"/api/v1/images/{image['id']}/restore", headers=h)
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert (await client.post(f"/api/v1/images/{image['id']}/restore", headers=h)).status_code == 409


async def test_documents_are_edited_archived_and_restored_never_deleted(client, clinic_with_users, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "STORAGE_LOCAL_PATH", str(tmp_path))
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    doc = (
        await client.post(
            f"/api/v1/patients/{patient_id}/documents",
            files={"file": ("informe.txt", b"contenido", "text/plain")},
            data={"title": "Informe", "document_type": "informe"},
            headers=h,
        )
    ).json()

    edited = await client.put(
        f"/api/v1/documents/{doc['id']}", json={"title": "Informe radiológico", "document_type": "informe"}, headers=h
    )
    assert edited.json()["title"] == "Informe radiológico"

    await client.post(f"/api/v1/documents/{doc['id']}/archive", json={"reason": "Duplicado"}, headers=h)
    active = (await client.get(f"/api/v1/patients/{patient_id}/documents", headers=h)).json()
    assert active == []
    everything = (await client.get(f"/api/v1/patients/{patient_id}/documents?include_archived=true", headers=h)).json()
    assert everything[0]["archived_reason"] == "Duplicado"
    # Archivado no es borrado: el archivo se sigue pudiendo descargar.
    assert (await client.get(f"/api/v1/documents/{doc['id']}/download", headers=h)).status_code == 200

    await client.post(f"/api/v1/documents/{doc['id']}/restore", headers=h)
    assert len((await client.get(f"/api/v1/patients/{patient_id}/documents", headers=h)).json()) == 1


async def test_consent_can_be_revoked_and_a_voided_one_not_signed(client, clinic_with_users):
    h = _auth(await _token(client))
    patient_id = await _patient(client, h["Authorization"].split()[1])
    consent = (
        await client.post(
            f"/api/v1/patients/{patient_id}/consents", json={"title": "Exodoncia", "body": "Texto"}, headers=h
        )
    ).json()

    voided = await client.post(f"/api/v1/consents/{consent['id']}/void", json={"reason": "Emitido por error"}, headers=h)
    assert voided.status_code == 200
    assert voided.json()["void_reason"] == "Emitido por error"
    sign = await client.put(f"/api/v1/consents/{consent['id']}/sign", json={"signed_by_name": "Lucía"}, headers=h)
    assert sign.status_code == 400

    signed = (
        await client.post(
            f"/api/v1/patients/{patient_id}/consents", json={"title": "Endodoncia", "body": "Texto"}, headers=h
        )
    ).json()
    await client.put(f"/api/v1/consents/{signed['id']}/sign", json={"signed_by_name": "Lucía"}, headers=h)
    revoked = await client.post(
        f"/api/v1/consents/{signed['id']}/void", json={"reason": "El paciente revoca antes del procedimiento"}, headers=h
    )
    assert revoked.status_code == 200
    # La firma original sigue a la vista junto con la revocación.
    assert revoked.json()["signed_by_name"] == "Lucía"
