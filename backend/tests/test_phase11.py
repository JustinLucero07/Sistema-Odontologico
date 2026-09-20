"""Phase 11: messaging, the assistant, and the patient portal.

This is the phase where it would be easiest to build something that looks like
it works. These tests are about the opposite: that a simulated message is never
called sent, that the assistant refuses to invent, and that a portal link is a
credential that expires, can be revoked, and shows nothing clinical.
"""

from datetime import datetime, timedelta, timezone

import pytest


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _patient(client, token, **extra) -> str:
    created = await client.post(
        "/api/v1/patients",
        json={"first_name": "Lucía", "last_name": "Arce", **extra},
        headers=_auth(token),
    )
    return created.json()["id"]


# ---- Messaging honesty --------------------------------------------------


async def test_a_message_with_no_provider_is_simulated_not_sent(client, clinic_with_users):
    """The whole point of the module: a clinic that believes a reminder went
    out stops calling the patient."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token, whatsapp="+34600111222")

    status = (await client.get("/api/v1/messaging/status", headers=_auth(token))).json()
    assert status["is_live"] is False
    assert "simulado" in status["message"]

    response = await client.post(
        "/api/v1/messaging/messages",
        json={"patient_id": patient_id, "channel": "whatsapp", "body": "Hola, le recordamos su cita."},
        headers=_auth(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "simulado"
    assert body["status"] != "enviado"
    # No delivery, so no moment of delivery.
    assert body["sent_at"] is None


async def test_a_patient_without_a_number_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)

    response = await client.post(
        "/api/v1/messaging/messages",
        json={"patient_id": patient_id, "channel": "whatsapp", "body": "Hola"},
        headers=_auth(token),
    )
    assert response.status_code == 422
    assert "WhatsApp" in response.json()["detail"]


async def test_templates_are_seeded_and_rendered(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token, whatsapp="+34600111222")

    templates = (await client.get("/api/v1/messaging/templates", headers=_auth(token))).json()
    assert any(t["code"] == "recordatorio_cita" for t in templates)

    response = await client.post(
        "/api/v1/messaging/messages",
        json={"patient_id": patient_id, "channel": "whatsapp", "template_code": "recitacion"},
        headers=_auth(token),
    )
    assert response.status_code == 201
    assert "Lucía" in response.json()["body"]


async def _appointment_with_due_reminder(client, token, db_session, patient_id):
    """Creates an appointment and drags its reminder into the past.

    Scheduling deliberately never produces an already-due reminder — one whose
    moment has passed is dropped at creation. So testing the DISPATCHER means
    backdating the row, rather than testing the scheduler a second time."""
    from sqlalchemy import select

    from app.modules.appointments.models import AppointmentReminder

    professional = (
        await client.post(
            "/api/v1/professionals",
            json={"first_name": "Rubén", "last_name": "Salas"},
            headers=_auth(token),
        )
    ).json()
    starts = datetime.now(timezone.utc) + timedelta(days=3)
    created = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional["id"],
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(minutes=30)).isoformat(),
            "reminder_channels": ["whatsapp"],
        },
        headers=_auth(token),
    )
    assert created.status_code == 201

    reminders = (
        await db_session.execute(
            select(AppointmentReminder).where(
                AppointmentReminder.appointment_id == created.json()["id"]
            )
        )
    ).scalars().all()
    assert reminders, "el alta debería haber programado recordatorios"
    for reminder in reminders:
        reminder.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db_session.commit()
    return created.json()["id"]


async def test_dispatch_resolves_due_reminders_once(client, clinic_with_users, db_session):
    """Running the dispatcher twice must not send the same reminder twice."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token, whatsapp="+34600111222")
    await _appointment_with_due_reminder(client, token, db_session, patient_id)

    first = (await client.post("/api/v1/messaging/dispatch", headers=_auth(token))).json()
    second = (await client.post("/api/v1/messaging/dispatch", headers=_auth(token))).json()

    assert first["due"] >= 1
    assert first["simulated"] >= 1
    # Nothing is due the second time: the reminders were resolved.
    assert second["due"] == 0


async def test_cancelling_an_appointment_resolves_its_reminders(
    client, clinic_with_users, db_session
):
    """The first line of defence lives in the appointments module: cancelling
    marks the pending reminders cancelled, so the dispatcher never sees them."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token, whatsapp="+34600111222")
    appointment_id = await _appointment_with_due_reminder(client, token, db_session, patient_id)

    await client.put(
        f"/api/v1/appointments/{appointment_id}/status",
        json={"status": "cancelada", "cancellation_reason": "El paciente avisó"},
        headers=_auth(token),
    )

    result = (await client.post("/api/v1/messaging/dispatch", headers=_auth(token))).json()
    assert result["due"] == 0
    assert result["sent"] == 0
    assert result["simulated"] == 0


async def test_dispatcher_refuses_a_reminder_for_a_dead_appointment(
    client, clinic_with_users, db_session
):
    """The dispatcher's own guard, checked on its own.

    Here the appointment is cancelled directly in the database, leaving the
    reminder pending — the state some other code path could one day produce.
    The dispatcher must still refuse to message a patient who is not coming."""
    from sqlalchemy import select

    from app.modules.appointments.models import Appointment

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token, whatsapp="+34600111222")
    appointment_id = await _appointment_with_due_reminder(client, token, db_session, patient_id)

    appointment = (
        await db_session.execute(select(Appointment).where(Appointment.id == appointment_id))
    ).scalar_one()
    appointment.status = "cancelada"
    await db_session.commit()

    result = (await client.post("/api/v1/messaging/dispatch", headers=_auth(token))).json()
    assert result["due"] >= 1
    assert result["skipped"] == result["due"]
    assert result["sent"] == 0
    assert result["simulated"] == 0


# ---- Assistant guardrails ----------------------------------------------


def test_guardrails_block_prices_and_diagnoses():
    """These run on every completion before anyone sees it."""
    from app.shared.ai import GuardrailViolation, check_output

    check_output("El paciente tiene una cita el 12 de marzo. No consta alergia.")

    for forbidden in [
        "El tratamiento cuesta $450.",
        "El precio es 200 USD.",
        "Recomiendo realizar una endodoncia.",
        "El diagnóstico probable es una caries profunda.",
    ]:
        with pytest.raises(GuardrailViolation):
            check_output(forbidden)


async def test_assistant_is_off_without_a_key_and_says_so(client, clinic_with_users):
    """No canned paragraph: a plausible sentence nobody generated is worse
    than a clear 'not configured'."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)

    status = (await client.get("/api/v1/ai/status", headers=_auth(token))).json()
    assert status["is_available"] is False
    assert "no está configurado" in status["message"]

    response = await client.post(
        f"/api/v1/patients/{patient_id}/ai/suggestions",
        json={"kind": "resumen_historia"},
        headers=_auth(token),
    )
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


async def test_the_context_contains_only_this_patients_record(client, clinic_with_users):
    """The assistant's whole world, exposed so it can be checked before its
    output is trusted."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    mine = await _patient(client, token)
    await client.post(
        "/api/v1/patients",
        json={"first_name": "Otro", "last_name": "Paciente"},
        headers=_auth(token),
    )
    await client.post(
        f"/api/v1/patients/{mine}/diagnoses",
        json={"description": "Caries oclusal en 36", "fdi_number": "36"},
        headers=_auth(token),
    )

    context = (
        await client.get(f"/api/v1/patients/{mine}/ai/context", headers=_auth(token))
    ).json()["context"]

    assert "Lucía Arce" in context
    assert "Caries oclusal en 36" in context
    assert "Otro Paciente" not in context
    # Nothing economic is ever handed over.
    assert "$" not in context
    assert "precio" not in context.lower()


async def test_an_accepted_suggestion_does_not_become_a_clinical_record(
    client, clinic_with_users, db_session
):
    """Accepting marks who took responsibility. It writes nothing into the
    record: putting the text into an evolution is a separate, deliberate act."""
    from sqlalchemy import select

    from app.modules.ai_assist.models import AiSuggestion
    from app.modules.clinical_evolution.models import ClinicalEvolution

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)

    suggestion = AiSuggestion(
        clinic_id=(await db_session.execute(select(AiSuggestion.clinic_id).limit(1))).scalar()
        or (await _clinic_id(db_session)),
        patient_id=patient_id,
        kind="borrador_mensaje",
        context_used="contexto de prueba",
        output="Hola, le esperamos en su próxima visita.",
        status="borrador",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(suggestion)
    await db_session.commit()

    accepted = await client.post(
        f"/api/v1/ai/suggestions/{suggestion.id}/accept", headers=_auth(token)
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "aceptado"
    assert accepted.json()["accepted_by_id"] is not None

    evolutions = (
        await db_session.execute(
            select(ClinicalEvolution).where(ClinicalEvolution.patient_id == patient_id)
        )
    ).scalars().all()
    assert evolutions == []

    # And it cannot be decided twice.
    again = await client.post(
        f"/api/v1/ai/suggestions/{suggestion.id}/accept", headers=_auth(token)
    )
    assert again.status_code == 409


async def _clinic_id(db_session):
    from sqlalchemy import select

    from app.modules.clinics.models import Clinic

    return (await db_session.execute(select(Clinic.id).limit(1))).scalar()


# ---- Patient portal -----------------------------------------------------


async def test_portal_link_is_shown_once_and_stored_hashed(
    client, clinic_with_users, db_session
):
    from sqlalchemy import select

    from app.modules.portal.models import PortalAccess

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/portal", headers=_auth(token)
    )
    assert created.status_code == 201
    url = created.json()["url"]
    raw = url.rsplit("/", 1)[-1]

    stored = (
        await db_session.execute(select(PortalAccess).where(PortalAccess.patient_id == patient_id))
    ).scalar_one()
    # A database dump must not hand anyone a working key.
    assert stored.token_hash != raw
    assert raw not in stored.token_hash

    # Listing the links never returns the token again.
    listing = (
        await client.get(f"/api/v1/patients/{patient_id}/portal", headers=_auth(token))
    ).json()
    assert "url" not in listing[0]
    assert "token" not in str(listing[0]).lower()


async def test_portal_view_needs_no_login_and_hides_clinical_data(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        json={"description": "Caries oclusal en 36", "fdi_number": "36"},
        headers=_auth(token),
    )
    raw = (
        await client.post(f"/api/v1/patients/{patient_id}/portal", headers=_auth(token))
    ).json()["url"].rsplit("/", 1)[-1]

    # No Authorization header: the token IS the credential.
    view = await client.get(f"/api/v1/portal/view/{raw}")
    assert view.status_code == 200
    body = view.json()
    assert body["patient_name"] == "Lucía Arce"
    # A link can land in the wrong inbox, so the blast radius stays small.
    assert "Caries" not in str(body)
    assert "diagnos" not in str(body).lower()


async def test_a_revoked_link_stops_working(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    created = (
        await client.post(f"/api/v1/patients/{patient_id}/portal", headers=_auth(token))
    ).json()
    raw = created["url"].rsplit("/", 1)[-1]

    assert (await client.get(f"/api/v1/portal/view/{raw}")).status_code == 200

    revoked = await client.post(
        f"/api/v1/portal/{created['id']}/revoke",
        json={"reason": "El paciente pidió darlo de baja"},
        headers=_auth(token),
    )
    assert revoked.status_code == 200
    assert (await client.get(f"/api/v1/portal/view/{raw}")).status_code == 404


async def test_unknown_and_expired_tokens_are_indistinguishable(client, clinic_with_users):
    """Telling an anonymous caller which it is would let them map live links."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    created = (
        await client.post(f"/api/v1/patients/{patient_id}/portal", headers=_auth(token))
    ).json()
    raw = created["url"].rsplit("/", 1)[-1]
    await client.post(
        f"/api/v1/portal/{created['id']}/revoke", json={"reason": "x"}, headers=_auth(token)
    )

    revoked = await client.get(f"/api/v1/portal/view/{raw}")
    unknown = await client.get(f"/api/v1/portal/view/{'z' * 60}")
    assert revoked.status_code == unknown.status_code == 404
    assert revoked.json()["detail"] == unknown.json()["detail"]


async def test_portal_use_is_counted(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _patient(client, token)
    raw = (
        await client.post(f"/api/v1/patients/{patient_id}/portal", headers=_auth(token))
    ).json()["url"].rsplit("/", 1)[-1]

    await client.get(f"/api/v1/portal/view/{raw}")
    await client.get(f"/api/v1/portal/view/{raw}")

    links = (
        await client.get(f"/api/v1/patients/{patient_id}/portal", headers=_auth(token))
    ).json()
    assert links[0]["use_count"] == 2
    assert links[0]["last_used_at"] is not None
