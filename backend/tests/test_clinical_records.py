async def _login(client, email, password):
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


async def _create_patient(client, token, first_name="Rosa") -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": first_name, "last_name": "Castro"}, headers=_auth(token)
    )
    return created.json()["id"]


# ---- Clinical evolutions -------------------------------------------------


async def test_create_and_list_evolution(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/evolutions",
        json={
            "procedure": "Restauración de resina en 46",
            "fdi_numbers": "46",
            "anesthesia": "Lidocaína 2%",
            "materials": "Resina compuesta A2",
            "instructions": "No masticar del lado derecho por 2 horas",
        },
        headers=_auth(token),
    )
    assert created.status_code == 201
    assert created.json()["procedure"] == "Restauración de resina en 46"

    listing = await client.get(f"/api/v1/patients/{patient_id}/evolutions", headers=_auth(token))
    assert len(listing.json()) == 1


async def test_evolution_has_no_delete_endpoint(client, clinic_with_users):
    """Clinical notes are never removed — only corrected, and that leaves a trail."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    created = await client.post(
        f"/api/v1/patients/{patient_id}/evolutions",
        json={"procedure": "Limpieza"},
        headers=_auth(token),
    )
    evolution_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/evolutions/{evolution_id}", headers=_auth(token))
    assert deleted.status_code == 405


async def test_correcting_an_evolution_keeps_an_audit_trail(client, clinic_with_users, db_session):
    from sqlalchemy import select

    from app.modules.audit.models import AuditLog

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    created = await client.post(
        f"/api/v1/patients/{patient_id}/evolutions",
        json={"procedure": "Extracción de 38"},
        headers=_auth(token),
    )
    evolution_id = created.json()["id"]

    updated = await client.put(
        f"/api/v1/evolutions/{evolution_id}",
        json={"procedure": "Extracción de 48 (corrección)"},
        headers=_auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["procedure"] == "Extracción de 48 (corrección)"

    logs = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "clinical_evolution", AuditLog.entity_id == evolution_id
            )
        )
    ).scalars().all()
    update_log = next(log for log in logs if log.action == "update")
    assert update_log.before["procedure"] == "Extracción de 38"


# ---- Prescriptions -------------------------------------------------------


async def test_create_prescription_with_items(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions",
        json={
            "professional_id": await _prescriber(client, _auth(token)),
            "notes": "Tomar con alimentos",
            "items": [
                {
                    "medication": "Amoxicilina 500 mg",
                    "dosage": "1 cápsula",
                    "frequency": "cada 8 horas",
                    "duration": "7 días",
                },
                {"medication": "Ibuprofeno 400 mg", "frequency": "cada 8 horas", "duration": "3 días"},
            ],
        },
        headers=_auth(token),
    )
    assert created.status_code == 201
    assert len(created.json()["items"]) == 2


async def test_prescription_requires_at_least_one_medication(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions", json={"items": []}, headers=_auth(token)
    )
    assert response.status_code == 422


# ---- Consents ------------------------------------------------------------


async def test_consent_snapshots_the_template_wording(client, clinic_with_users):
    """Editing a template afterwards must not change what a patient already
    agreed to."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    template = await client.post(
        "/api/v1/consents/templates",
        json={
            "name": "Consentimiento de extracción",
            "procedure_type": "extraccion",
            "body": "Texto original de la extracción.",
        },
        headers=_auth(token),
    )
    template_id = template.json()["id"]

    consent = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        json={"template_id": template_id},
        headers=_auth(token),
    )
    assert consent.status_code == 201
    assert consent.json()["body"] == "Texto original de la extracción."
    assert consent.json()["status"] == "pendiente"

    # A new template with different wording does not rewrite the signed record.
    listing = await client.get(f"/api/v1/patients/{patient_id}/consents", headers=_auth(token))
    assert listing.json()[0]["body"] == "Texto original de la extracción."


async def test_consent_signing_flow(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    consent = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        json={"title": "Consentimiento de endodoncia", "body": "Acepto el procedimiento."},
        headers=_auth(token),
    )
    consent_id = consent.json()["id"]

    signed = await client.put(
        f"/api/v1/consents/{consent_id}/sign",
        json={"signed_by_name": "Rosa Castro"},
        headers=_auth(token),
    )
    assert signed.status_code == 200
    assert signed.json()["status"] == "firmado"
    assert signed.json()["signed_at"] is not None

    twice = await client.put(
        f"/api/v1/consents/{consent_id}/sign",
        json={"signed_by_name": "Otra persona"},
        headers=_auth(token),
    )
    assert twice.status_code == 400


async def test_consent_without_template_or_text_is_rejected(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/consents", json={}, headers=_auth(token)
    )
    assert response.status_code == 400


# ---- Documents -----------------------------------------------------------


async def test_upload_and_download_document(client, clinic_with_users, tmp_path, monkeypatch):
    from app.core.config import get_settings

    # Keep uploaded bytes inside the test's temp dir, not the dev storage folder.
    settings = get_settings()
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path))

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    upload = await client.post(
        f"/api/v1/patients/{patient_id}/documents",
        files={"file": ("informe.txt", b"contenido del informe", "text/plain")},
        data={"title": "Informe radiológico", "document_type": "informe"},
        headers=_auth(token),
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["title"] == "Informe radiológico"
    assert body["size_bytes"] == len(b"contenido del informe")

    download = await client.get(f"/api/v1/documents/{body['id']}/download", headers=_auth(token))
    assert download.status_code == 200
    assert download.content == b"contenido del informe"


async def test_empty_upload_is_rejected(client, clinic_with_users, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "STORAGE_LOCAL_PATH", str(tmp_path))

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/documents",
        files={"file": ("vacio.txt", b"", "text/plain")},
        data={"title": "Vacío", "document_type": "otro"},
        headers=_auth(token),
    )
    assert response.status_code == 400


async def test_role_without_prescriptions_write_cannot_prescribe(client, clinic_with_users, db_session):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "prescriptions:write"]
    await db_session.flush()
    await db_session.commit()

    dentist_token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions",
        json={"items": [{"medication": "Paracetamol"}]},
        headers=_auth(dentist_token),
    )
    assert response.status_code == 403


async def test_prescription_needs_an_active_prescriber(client, clinic_with_users):
    """Una receta sin quien la firme no es un documento válido."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    items = [{"medication": "Paracetamol 500 mg"}]

    missing = await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions", json={"items": items}, headers=_auth(token)
    )
    assert missing.status_code == 422

    prescriber = await _prescriber(client, _auth(token))
    await client.put(f"/api/v1/professionals/{prescriber}", json={"is_active": False}, headers=_auth(token))
    inactive = await client.post(
        f"/api/v1/patients/{patient_id}/prescriptions",
        json={"professional_id": prescriber, "items": items},
        headers=_auth(token),
    )
    assert inactive.status_code == 400
