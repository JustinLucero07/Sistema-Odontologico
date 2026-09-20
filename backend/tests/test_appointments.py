from datetime import datetime, timedelta, timezone


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client, token, first_name="Nuria") -> str:
    created = await client.post(
        "/api/v1/patients", json={"first_name": first_name, "last_name": "Salas"}, headers=_auth(token)
    )
    return created.json()["id"]


async def _create_professional(client, token, first_name="Ana") -> str:
    created = await client.post(
        "/api/v1/professionals", json={"first_name": first_name, "last_name": "Molina"}, headers=_auth(token)
    )
    return created.json()["id"]


def _slot(days_ahead: int = 1, hour: int = 10, minutes: int = 30) -> tuple[str, str]:
    start = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return start.isoformat(), (start + timedelta(minutes=minutes)).isoformat()


async def test_create_appointment_schedules_default_reminders(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    professional_id = await _create_professional(client, token)
    # Far enough out that both the 24 h and the 2 h reminder still lie ahead.
    starts_at, ends_at = _slot(days_ahead=4)

    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "reminder_channels": ["whatsapp"],
        },
        headers=_auth(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "programada"
    assert body["duration_minutes"] == 30
    assert body["patient_name"].startswith("Nuria")
    # 24 h and 2 h before, on the requested channel
    assert len(body["reminders"]) == 2
    assert {r["offset_minutes"] for r in body["reminders"]} == {1440, 120}
    assert all(r["status"] == "pendiente" for r in body["reminders"])


async def test_reminder_whose_moment_already_passed_is_not_scheduled(client, clinic_with_users):
    """Booking an appointment for later today must not create a 24 h reminder
    that would already be overdue the moment it is written."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    professional_id = await _create_professional(client, token)

    start = datetime.now(timezone.utc) + timedelta(hours=6)
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(minutes=30)).isoformat(),
            "reminder_channels": ["whatsapp"],
        },
        headers=_auth(token),
    )
    assert response.status_code == 201
    offsets = {r["offset_minutes"] for r in response.json()["reminders"]}
    assert offsets == {120}


async def test_double_booking_same_professional_is_rejected(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    professional_id = await _create_professional(client, token)
    first_patient = await _create_patient(client, token, "Primera")
    second_patient = await _create_patient(client, token, "Segunda")
    starts_at, ends_at = _slot(hour=9)

    first = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": first_patient,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers=_auth(token),
    )
    assert first.status_code == 201

    overlapping = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": second_patient,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers=_auth(token),
    )
    assert overlapping.status_code == 409


async def test_back_to_back_appointments_are_allowed(client, clinic_with_users):
    """The slot range is half-open, so an appointment can start exactly when
    the previous one ends."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    professional_id = await _create_professional(client, token)
    patient_id = await _create_patient(client, token)

    start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
        hour=8, minute=0, second=0, microsecond=0
    )
    middle = start + timedelta(minutes=30)
    end = start + timedelta(minutes=60)

    first = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": start.isoformat(),
            "ends_at": middle.isoformat(),
        },
        headers=_auth(token),
    )
    second = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": middle.isoformat(),
            "ends_at": end.isoformat(),
        },
        headers=_auth(token),
    )
    assert first.status_code == 201
    assert second.status_code == 201


async def test_cancelling_frees_the_slot_and_cancels_reminders(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    professional_id = await _create_professional(client, token)
    patient_id = await _create_patient(client, token)
    starts_at, ends_at = _slot(days_ahead=3, hour=11)

    booked = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "reminder_channels": ["email"],
        },
        headers=_auth(token),
    )
    appointment_id = booked.json()["id"]

    cancelled = await client.put(
        f"/api/v1/appointments/{appointment_id}/status",
        json={"status": "cancelada", "cancellation_reason": "El paciente reprogramó"},
        headers=_auth(token),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelada"
    assert all(r["status"] == "cancelado" for r in cancelled.json()["reminders"])

    # the freed slot can be booked again
    rebooked = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers=_auth(token),
    )
    assert rebooked.status_code == 201


async def test_agenda_range_query_and_patient_history(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    professional_id = await _create_professional(client, token)
    patient_id = await _create_patient(client, token)
    starts_at, ends_at = _slot(days_ahead=5, hour=15)

    await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers=_auth(token),
    )

    day_start = datetime.fromisoformat(starts_at).replace(hour=0, minute=0)
    day_end = day_start + timedelta(days=1)
    agenda = await client.get(
        "/api/v1/appointments",
        params={"from": day_start.isoformat(), "to": day_end.isoformat()},
        headers=_auth(token),
    )
    assert agenda.status_code == 200
    assert len(agenda.json()) == 1

    empty_day = await client.get(
        "/api/v1/appointments",
        params={
            "from": (day_start + timedelta(days=10)).isoformat(),
            "to": (day_end + timedelta(days=10)).isoformat(),
        },
        headers=_auth(token),
    )
    assert empty_day.json() == []

    patient_agenda = await client.get(f"/api/v1/patients/{patient_id}/appointments", headers=_auth(token))
    assert len(patient_agenda.json()) == 1


async def test_rescheduling_moves_pending_reminders(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    professional_id = await _create_professional(client, token)
    patient_id = await _create_patient(client, token)
    starts_at, ends_at = _slot(days_ahead=6, hour=9)

    booked = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "reminder_channels": ["whatsapp"],
        },
        headers=_auth(token),
    )
    appointment_id = booked.json()["id"]
    original_reminder = min(r["scheduled_for"] for r in booked.json()["reminders"])

    new_start = datetime.fromisoformat(starts_at) + timedelta(days=1)
    new_end = datetime.fromisoformat(ends_at) + timedelta(days=1)
    moved = await client.put(
        f"/api/v1/appointments/{appointment_id}",
        json={"starts_at": new_start.isoformat(), "ends_at": new_end.isoformat()},
        headers=_auth(token),
    )
    assert moved.status_code == 200
    assert min(r["scheduled_for"] for r in moved.json()["reminders"]) > original_reminder


async def test_role_without_appointments_write_cannot_book(client, clinic_with_users, db_session):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    professional_id = await _create_professional(client, token)
    patient_id = await _create_patient(client, token)
    starts_at, ends_at = _slot(days_ahead=7)

    dentist_role = clinic_with_users["roles"]["Odontólogo"]
    dentist_role.permissions = [p for p in dentist_role.permissions if p.code != "appointments:write"]
    await db_session.flush()
    await db_session.commit()

    dentist_token = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers=_auth(dentist_token),
    )
    assert response.status_code == 403
