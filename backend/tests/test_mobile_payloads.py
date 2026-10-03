"""Contrato con la app móvil.

Cada petición de este archivo es exactamente la que arma un formulario de la
app (mobile/lib/...): los mismos campos, con los mismos tipos (los importes
como texto con punto decimal, los opcionales vacíos como null). Si el backend
cambia un esquema y la app deja de poder guardar, esto falla aquí antes que en
el teléfono de la clínica.
"""

from datetime import date, datetime, timedelta, timezone


async def _token(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Token-Delivery": "body"}


def _ok(r, code=(200, 201)):
    assert r.status_code in (code if isinstance(code, tuple) else (code,)), r.text
    return r.json()


async def test_mobile_patient_and_clinical_forms(client, clinic_with_users):
    h = await _token(client)

    # pestanas.dart · editarPaciente (alta)
    patient = _ok(
        await client.post(
            "/api/v1/patients",
            json={
                "first_name": "Ana",
                "last_name": "Mora",
                "national_id": None,
                "birth_date": "1990-04-12",
                "sex": "F",
                "occupation": None,
                "phone": "0999000111",
                "whatsapp": "0999000111",
                "email": "ana@example.com",
                "address": None,
                "city": "Quito",
                "emergency_contact_name": None,
                "emergency_contact_phone": None,
                "notes": None,
            },
            headers=h,
        )
    )
    pid = patient["id"]
    _ok(await client.put(f"/api/v1/patients/{pid}", json={"first_name": "Ana", "last_name": "Mora", "city": "Cuenca"}, headers=h))

    # nuevaVersionHistoria
    _ok(await client.post(f"/api/v1/patients/{pid}/medical-history", json={"allergies": "Penicilina", "observations": None}, headers=h))

    # profesional y tratamiento (configuracion_pages.dart)
    prof = _ok(
        await client.post(
            "/api/v1/professionals",
            json={"first_name": "Luis", "last_name": "Paz", "specialty_id": None, "license_number": None, "color_hex": "#0F6FFF"},
            headers=h,
        )
    )
    treat = _ok(await client.post("/api/v1/treatments", json={"name": "Resina", "default_price": "45.50", "description": None}, headers=h))

    # editarPlan + _editarItem (precio tomado del catálogo como número)
    plan = _ok(await client.post(f"/api/v1/patients/{pid}/treatment-plans", json={"title": "Plan", "notes": None, "items": []}, headers=h))
    item = _ok(
        await client.post(
            f"/api/v1/treatment-plans/{plan['id']}/items",
            json={
                "treatment_id": treat["id"],
                "fdi_number": "16",
                "surface": None,
                "price": treat["default_price"],
                "discount": 0,
                "status": "propuesto",
                "professional_id": None,
                "estimated_date": None,
                "notes": None,
            },
            headers=h,
        )
    )
    # La respuesta es el plan, y ya trae el ítem recién agregado.
    assert len(item["items"]) == 1
    item_id = item["items"][0]["id"]
    _ok(
        await client.put(
            f"/api/v1/treatment-plans/{plan['id']}/items/{item_id}",
            json={"fdi_number": "16", "price": "40.00", "discount": "5", "status": "completado"},
            headers=h,
        )
    )

    # registrarEvolucion, nuevaReceta, nuevoDiagnostico
    _ok(
        await client.post(
            f"/api/v1/patients/{pid}/evolutions",
            json={"procedure": "Resina oclusal", "fdi_numbers": "16", "professional_id": prof["id"], "diagnosis": None},
            headers=h,
        )
    )
    _ok(
        await client.post(
            f"/api/v1/patients/{pid}/prescriptions",
            json={
                "professional_id": prof["id"],
                "notes": None,
                "items": [{"medication": "Ibuprofeno 400 mg", "dosage": "1 tableta", "frequency": "c/8h", "duration": "3 días", "instructions": None}],
            },
            headers=h,
        )
    )
    _ok(await client.post(f"/api/v1/patients/{pid}/diagnoses", json={"description": "Caries", "fdi_number": "16", "notes": None}, headers=h))

    # odontograma: nueva versión con notas nulas
    _ok(
        await client.post(
            f"/api/v1/patients/{pid}/odontogram",
            json={"conditions": [{"fdi_number": "16", "surface": "oclusal", "condition": "caries", "notes": None}]},
            headers=h,
        )
    )

    # cita_form.dart · editarCita (UTC con «Z» del toIso8601String de Dart)
    start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    cita = _ok(
        await client.post(
            "/api/v1/appointments",
            json={
                "patient_id": pid,
                "professional_id": prof["id"],
                "treatment_id": None,
                "starts_at": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "ends_at": (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "notes": None,
            },
            headers=h,
        )
    )
    _ok(
        await client.put(
            f"/api/v1/appointments/{cita['id']}",
            json={
                "professional_id": prof["id"],
                "treatment_id": treat["id"],
                "starts_at": (start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "ends_at": (start + timedelta(hours=1, minutes=45)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "notes": "Traer radiografía",
            },
            headers=h,
        )
    )
    _ok(await client.put(f"/api/v1/appointments/{cita['id']}/status", json={"status": "cancelada", "cancellation_reason": None}, headers=h))

    # imagen (multiparte con todos los campos como texto)
    r = await client.post(
        f"/api/v1/patients/{pid}/images",
        files={"file": ("foto.png", _png(), "image/png")},
        data={"title": "Intraoral", "image_type": "foto_intraoral", "fdi_numbers": "16,17", "taken_on": date.today().isoformat()},
        headers=h,
    )
    image = _ok(r)
    _ok(
        await client.put(
            f"/api/v1/images/{image['id']}",
            json={"title": "Intraoral 16", "image_type": "foto_intraoral", "fdi_numbers": ["16"], "taken_on": None, "description": None},
            headers=h,
        )
    )
    _ok(await client.post(f"/api/v1/images/{image['id']}/archive", json={"reason": "Borrosa"}, headers=h))


async def test_mobile_money_forms(client, clinic_with_users):
    h = await _token(client)
    pid = _ok(await client.post("/api/v1/patients", json={"first_name": "Leo", "last_name": "Ruiz"}, headers=h))["id"]

    # caja_page.dart
    _ok(await client.post("/api/v1/finance/cash-session/open", json={"opening_float": "20"}, headers=h))

    # pestanas.dart · nuevoCargo, registrarCobro, financiarCargo
    charge = _ok(
        await client.post(
            f"/api/v1/patients/{pid}/charges",
            json={"description": "Ortodoncia", "amount": "600", "issued_on": date.today().isoformat(), "notes": None},
            headers=h,
        )
    )
    _ok(
        await client.post(
            f"/api/v1/patients/{pid}/payments",
            json={"amount": "10.5", "method": "efectivo", "charge_id": None, "reference": None, "received_on": date.today().isoformat(), "notes": None},
            headers=h,
        )
    )
    credit = _ok(
        await client.post(
            f"/api/v1/patients/{pid}/credits",
            json={
                "installment_count": 3,
                "frequency": "mensual",
                "first_due_on": (date.today() + timedelta(days=30)).isoformat(),
                "monthly_rate": "0",
                "down_payment": "0",
                "down_payment_method": "efectivo",
                "guarantor_name": None,
                "guarantor_id_number": None,
                "guarantor_phone": None,
                "notes": None,
                "charge_id": charge["id"],
            },
            headers=h,
        )
    )
    # creditos_page.dart
    _ok(await client.post(f"/api/v1/credits/{credit['id']}/payments", json={"amount": "100", "method": "efectivo", "reference": None, "notes": None}, headers=h))
    _ok(await client.put(f"/api/v1/credits/{credit['id']}", json={"guarantor_name": "Rosa", "guarantor_id_number": None, "guarantor_phone": "0999", "notes": None}, headers=h))
    _ok(
        await client.post(
            f"/api/v1/credits/{credit['id']}/restructure",
            json={"installment_count": 4, "frequency": "quincenal", "first_due_on": (date.today() + timedelta(days=15)).isoformat()},
            headers=h,
        )
    )

    # finanzas_page.dart · editarEgreso
    expense = _ok(
        await client.post(
            "/api/v1/finance/expenses",
            json={
                "spent_on": date.today().isoformat(),
                "category": "insumos",
                "description": "Guantes",
                "amount": "12.30",
                "method": "efectivo",
                "supplier_name": None,
                "receipt_number": None,
                "notes": None,
            },
            headers=h,
        )
    )
    _ok(
        await client.put(
            f"/api/v1/finance/expenses/{expense['id']}",
            json={"spent_on": date.today().isoformat(), "category": "insumos", "description": "Guantes nitrilo", "supplier_name": None, "receipt_number": "001", "notes": None},
            headers=h,
        )
    )
    _ok(await client.post(f"/api/v1/finance/expenses/{expense['id']}/void", json={"reason": "Duplicado"}, headers=h))

    _ok(await client.post("/api/v1/finance/cash-session/close", json={"counted_cash": "30.50", "notes": None}, headers=h))


async def test_mobile_inventory_lab_and_settings(client, clinic_with_users):
    h = await _token(client)
    pid = _ok(await client.post("/api/v1/patients", json={"first_name": "Eva", "last_name": "Sol"}, headers=h))["id"]

    # inventario_page.dart
    supplier = _ok(
        await client.post(
            "/api/v1/inventory/suppliers",
            json={"name": "Dental Sur", "contact_name": None, "phone": None, "email": None, "notes": None, "is_active": True},
            headers=h,
        )
    )
    item = _ok(
        await client.post(
            "/api/v1/inventory/items",
            json={
                "name": "Guantes",
                "unit": "caja",
                "minimum_stock": "5",
                "sku": None,
                "category": None,
                "unit_cost": None,
                "supplier_id": supplier["id"],
                "notes": None,
                "is_active": True,
            },
            headers=h,
        )
    )
    catalog = _ok(await client.get("/api/v1/inventory/catalog", headers=h))
    entrada = next(r["code"] for r in catalog["reasons"] if r["sign"] > 0)
    _ok(
        await client.post(
            f"/api/v1/inventory/items/{item['id']}/movements",
            json={"reason": entrada, "quantity": "10", "unit_cost": "3.20", "lot_number": None, "expires_on": None, "notes": None},
            headers=h,
        )
    )

    # laboratorio_page.dart
    lab = _ok(
        await client.post(
            "/api/v1/laboratory/laboratories",
            json={"name": "Lab Andes", "contact_name": None, "phone": None, "email": None, "address": None, "default_turnaround_days": 7, "notes": None, "is_active": True},
            headers=h,
        )
    )
    order = _ok(
        await client.post(
            "/api/v1/laboratory/orders",
            json={
                "patient_id": pid,
                "laboratory_id": lab["id"],
                "work_type": "corona",
                "description": "Corona zirconio 16",
                "fdi_numbers": ["16"],
                "shade": None,
                "material": None,
                "due_on": None,
                "cost": None,
                "notes": None,
            },
            headers=h,
        )
    )
    _ok(await client.put(f"/api/v1/laboratory/orders/{order['id']}/status", json={"status": "enviado", "note": None}, headers=h))

    # configuracion_pages.dart · UsuariosPage (rol único en role_ids)
    roles = _ok(await client.get("/api/v1/roles", headers=h))
    user = _ok(
        await client.post(
            "/api/v1/users",
            json={"first_name": "Rita", "last_name": "Vega", "email": "rita@clinicatest.io", "password": "Molar-Sano-48", "role_ids": [roles[0]["id"]]},
            headers=h,
        )
    )
    _ok(await client.put(f"/api/v1/users/{user['id']}", json={"first_name": "Rita", "last_name": "Vega", "role_ids": [roles[0]["id"]], "is_active": False}, headers=h))

    # ClinicaPage
    _ok(await client.put("/api/v1/clinics/me", json={"name": "Clínica Test", "legal_name": None, "tax_id": None, "phone": None, "email": None, "address": None}, headers=h))


def _png() -> bytes:
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
