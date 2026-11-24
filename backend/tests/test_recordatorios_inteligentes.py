import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.modules.appointments.models import Appointment, AppointmentReminder
from app.modules.insights.inteligencia import nivel
from app.modules.messaging.models import OutboundMessage
from app.modules.professionals.models import Professional


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_niveles_de_riesgo():
    assert nivel(0, 0) == "nuevo"
    assert nivel(0, 6) == "bajo"
    assert nivel(1, 10) == "bajo"
    assert nivel(1, 4) == "medio"
    assert nivel(2, 6) == "alto"
    assert nivel(3, 4) == "alto"


async def _historial(session_factory, clinic_id, patient_id, estados):
    async with session_factory() as db:
        prof = Professional(clinic_id=clinic_id, first_name="Laura", last_name="Vega")
        db.add(prof)
        await db.flush()
        base = datetime.now(timezone.utc) - timedelta(days=400)
        for i, estado in enumerate(estados):
            ini = base + timedelta(days=14 * i)
            db.add(Appointment(
                clinic_id=clinic_id, patient_id=patient_id, professional_id=prof.id,
                starts_at=ini, ends_at=ini + timedelta(minutes=30), status=estado,
            ))
        await db.commit()
        return prof.id


async def test_quien_suele_faltar_recibe_recordatorio_antes(client, session_factory, clinic_with_users):
    admin = await _h(client)
    clinic_id = clinic_with_users["clinic"].id
    pid = (await client.post("/api/v1/patients", json={"first_name": "Rosa", "last_name": "Ruiz", "phone": "0991111111"}, headers=admin)).json()["id"]
    prof_id = await _historial(session_factory, clinic_id, uuid.UUID(pid), ["atendida", "no_asistio", "atendida", "no_asistio", "no_asistio"])

    r = (await client.get(f"/api/v1/insights/no-show-risk?patient_ids={pid}", headers=admin)).json()
    assert r[0]["nivel"] == "alto"
    assert r[0]["texto"] == "Faltó a 3 de sus últimas 5 citas"

    ini = datetime.now(timezone.utc) + timedelta(days=5)
    cita = await client.post(
        "/api/v1/appointments",
        json={"patient_id": pid, "professional_id": str(prof_id), "starts_at": ini.isoformat(),
              "ends_at": (ini + timedelta(minutes=30)).isoformat(), "reminder_channels": ["whatsapp"]},
        headers=admin,
    )
    assert cita.status_code == 201, cita.text
    async with session_factory() as db:
        offsets = sorted(
            (await db.execute(select(AppointmentReminder.offset_minutes).where(AppointmentReminder.appointment_id == uuid.UUID(cita.json()["id"])))).scalars()
        )
    assert offsets == [120, 24 * 60, 72 * 60]

    async with session_factory() as db:
        temprano = (await db.execute(select(AppointmentReminder).where(
            AppointmentReminder.appointment_id == uuid.UUID(cita.json()["id"]), AppointmentReminder.offset_minutes == 72 * 60,
        ))).scalar_one()
        temprano.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()
    await client.post("/api/v1/messaging/dispatch", headers=admin)
    async with session_factory() as db:
        cuerpo = (await db.execute(select(OutboundMessage.body).where(OutboundMessage.patient_id == uuid.UUID(pid)))).scalar_one()
    assert "confírmenos su asistencia" in cuerpo


async def test_paciente_cumplido_recibe_los_de_siempre(client, session_factory, clinic_with_users):
    admin = await _h(client)
    clinic_id = clinic_with_users["clinic"].id
    pid = (await client.post("/api/v1/patients", json={"first_name": "Leo", "last_name": "Paz"}, headers=admin)).json()["id"]
    prof_id = await _historial(session_factory, clinic_id, uuid.UUID(pid), ["atendida"] * 4)
    ini = datetime.now(timezone.utc) + timedelta(days=5)
    cita = await client.post(
        "/api/v1/appointments",
        json={"patient_id": pid, "professional_id": str(prof_id), "starts_at": ini.isoformat(),
              "ends_at": (ini + timedelta(minutes=30)).isoformat(), "reminder_channels": ["whatsapp"]},
        headers=admin,
    )
    async with session_factory() as db:
        offsets = sorted(
            (await db.execute(select(AppointmentReminder.offset_minutes).where(AppointmentReminder.appointment_id == uuid.UUID(cita.json()["id"])))).scalars()
        )
    assert offsets == [120, 24 * 60]


async def test_a_quien_llamar_hoy(client, session_factory, clinic_with_users):
    admin = await _h(client)
    clinic_id = clinic_with_users["clinic"].id
    fiel = (await client.post("/api/v1/patients", json={"first_name": "Fiel", "last_name": "Uno", "phone": "0992222222"}, headers=admin)).json()["id"]
    falton = (await client.post("/api/v1/patients", json={"first_name": "Falta", "last_name": "Dos", "phone": "0993333333"}, headers=admin)).json()["id"]
    await _historial(session_factory, clinic_id, uuid.UUID(fiel), ["atendida"] * 5)
    await _historial(session_factory, clinic_id, uuid.UUID(falton), ["no_asistio", "atendida", "no_asistio"])

    r = await client.get("/api/v1/insights/call-today", headers=admin)
    assert r.status_code == 200, r.text
    data = r.json()
    nombres = [s["patient_name"] for s in data["sugerencias"]]
    assert "Fiel Uno" in nombres and "Falta Dos" in nombres
    assert nombres.index("Fiel Uno") < nombres.index("Falta Dos")
    fiel_s = next(s for s in data["sugerencias"] if s["patient_name"] == "Fiel Uno")
    assert fiel_s["motivo"] == "control"
    assert "Asistió a sus últimas 5 citas" in fiel_s["razones"]
    assert fiel_s["mensaje"].startswith("Hola Fiel")
    falta_s = next(s for s in data["sugerencias"] if s["patient_name"] == "Falta Dos")
    assert falta_s["riesgo"] == "alto"


async def test_requiere_sesion(client):
    assert (await client.get("/api/v1/insights/call-today")).status_code == 401
