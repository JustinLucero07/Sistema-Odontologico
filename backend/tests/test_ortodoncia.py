import io
import zipfile
from datetime import date, timedelta


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _paciente(client, h, nombre="Yajaira", apellido="Zumba"):
    r = await client.post("/api/v1/patients", json={"first_name": nombre, "last_name": apellido}, headers=h)
    return r.json()["id"]


async def test_ficha_cuotas_y_abonos(client):
    h = await _h(client)
    pid = await _paciente(client, h)
    r = await client.post("/api/v1/orthodontics/cases", json={"patient_id": pid, "agreed_total": "900"}, headers=h)
    assert r.status_code == 201, r.text
    caso = r.json()
    assert caso["code"] == "ORT-0001"
    assert caso["charge_id"]
    assert caso["docs_pending"] == 4

    # Una sola ficha abierta por paciente.
    r = await client.post("/api/v1/orthodontics/cases", json={"patient_id": pid}, headers=h)
    assert r.status_code == 409

    inicio = date.today() - timedelta(days=40)
    r = await client.post(
        f"/api/v1/orthodontics/cases/{caso['id']}/controls/generate",
        json={"count": 3, "first_on": inicio.isoformat(), "amount": "100"}, headers=h,
    )
    caso = r.json()
    assert caso["controls_count"] == 3
    assert caso["controls_total"] == "300.00"
    assert caso["difference"] == "-600.00"
    c1 = caso["controls"][0]
    assert c1["status"] == "vencida"
    assert caso["next_control_overdue"] is True

    # Registro clínico de la visita.
    r = await client.patch(
        f"/api/v1/orthodontics/controls/{c1['id']}",
        json={"attended_on": inicio.isoformat(), "arches": "14 NiTi sup", "elastics": "Clase II"}, headers=h,
    )
    assert r.json()["controls"][0]["arches"] == "14 NiTi sup"

    # Abono parcial y luego el resto.
    r = await client.post(
        f"/api/v1/orthodontics/controls/{c1['id']}/payments", json={"amount": "40", "method": "efectivo"}, headers=h
    )
    assert r.status_code == 201, r.text
    assert r.json()["controls"][0]["paid"] == "40.00"
    r = await client.post(
        f"/api/v1/orthodontics/controls/{c1['id']}/payments", json={"amount": "70", "method": "efectivo"}, headers=h
    )
    assert r.status_code == 422  # supera el saldo de la cuota
    r = await client.post(
        f"/api/v1/orthodontics/controls/{c1['id']}/payments", json={"amount": "60", "method": "efectivo"}, headers=h
    )
    caso = r.json()
    assert caso["controls"][0]["status"] == "pagada"
    assert caso["paid"] == "100.00"
    assert caso["balance"] == "800.00"

    # El pago aparece en la cuenta normal del paciente.
    cuenta = (await client.get(f"/api/v1/patients/{pid}/account", headers=h)).json()
    assert any(p.get("ortho_control_id") == c1["id"] for p in cuenta["payments"])

    # No se puede bajar la cuota por debajo de lo abonado ni borrarla.
    r = await client.patch(f"/api/v1/orthodontics/controls/{c1['id']}", json={"amount": "50"}, headers=h)
    assert r.status_code == 409
    r = await client.delete(f"/api/v1/orthodontics/controls/{c1['id']}", headers=h)
    assert r.status_code == 409

    # Anular un abono reabre la cuota.
    pago = caso["controls"][0]["payments"][0]["id"]
    r = await client.post(f"/api/v1/finance/payments/{pago}/void", json={"reason": "Error de digitación"}, headers=h)
    assert r.status_code in (200, 204), r.text
    caso = (await client.get(f"/api/v1/orthodontics/cases/{caso['id']}", headers=h)).json()
    assert caso["controls"][0]["status"] == "vencida"
    assert caso["paid"] == "60.00"

    r = await client.patch(f"/api/v1/orthodontics/cases/{caso['id']}", json={"agreed_total": "1000"}, headers=h)
    assert r.json()["balance"] == "940.00"
    r = await client.patch(f"/api/v1/orthodontics/cases/{caso['id']}", json={"agreed_total": "50"}, headers=h)
    assert r.status_code == 409

    # Borrar una cuota sin abonos renumera.
    c2 = caso["controls"][1]["id"]
    r = await client.delete(f"/api/v1/orthodontics/controls/{c2}", headers=h)
    assert [c["number"] for c in r.json()["controls"]] == [1, 2]

    # Exportaciones.
    r = await client.get(f"/api/v1/orthodontics/cases/{caso['id']}/export.csv", headers=h)
    assert r.status_code == 200 and "Arcos" in r.content.decode("utf-8-sig")
    r = await client.get(f"/api/v1/orthodontics/cases/{caso['id']}/export.pdf", headers=h)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    # Con abonos vigentes la ficha no se borra.
    r = await client.delete(f"/api/v1/orthodontics/cases/{caso['id']}", headers=h)
    assert r.status_code == 409


async def test_lista_y_filtros(client):
    h = await _h(client)
    a = await _paciente(client, h, "Andrea", "Merino")
    b = await _paciente(client, h, "Pablo", "Calva")
    ca = (await client.post("/api/v1/orthodontics/cases", json={"patient_id": a, "has_tad": "si"}, headers=h)).json()
    await client.post("/api/v1/orthodontics/cases", json={"patient_id": b, "doc_xrays": "listo", "doc_photos": "listo",
                                                          "doc_models": "no_requiere", "doc_folder": "listo"}, headers=h)
    todo = (await client.get("/api/v1/orthodontics/cases", headers=h)).json()
    assert todo["total"] == 2 and todo["active"] == 2
    assert len((await client.get("/api/v1/orthodontics/cases?has_tad=si", headers=h)).json()["items"]) == 1
    assert len((await client.get("/api/v1/orthodontics/cases?docs=completa", headers=h)).json()["items"]) == 1
    assert len((await client.get("/api/v1/orthodontics/cases?q=merino", headers=h)).json()["items"]) == 1
    assert len((await client.get("/api/v1/orthodontics/cases?next_control=sin_fecha", headers=h)).json()["items"]) == 2
    # Una ficha sin abonos se puede eliminar.
    assert (await client.delete(f"/api/v1/orthodontics/cases/{ca['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/patients/{a}/orthodontics", headers=h)).json() == []


async def test_activar_ortodoncia_en_la_clinica(client):
    h = await _h(client)
    assert (await client.get("/api/v1/clinics/branding", headers=h)).json()["orthodontics_enabled"] is False
    r = await client.put("/api/v1/clinics/me", json={"orthodontics_enabled": True}, headers=h)
    assert r.status_code == 200, r.text
    assert (await client.get("/api/v1/clinics/branding", headers=h)).json()["orthodontics_enabled"] is True


def _xlsx(filas: list[list[str]]) -> bytes:
    """Un .xlsx mínimo, como lo guarda Excel (cadenas en línea)."""
    def celda(i, j, v):
        ref = f"{chr(65 + j)}{i + 1}"
        return f'<c r="{ref}" t="inlineStr"><is><t>{v}</t></is></c>'
    hoja = "".join(
        f'<row r="{i + 1}">' + "".join(celda(i, j, v) for j, v in enumerate(f)) + "</row>" for i, f in enumerate(filas)
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Hoja1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   f"<sheetData>{hoja}</sheetData></worksheet>")
    return buf.getvalue()


async def test_importar_pacientes_csv_y_excel(client):
    h = await _h(client)
    await client.post("/api/v1/patients", json={"first_name": "Erick", "last_name": "Troya", "national_id": "0102030405"},
                      headers=h)
    csv = (
        "Listado de pacientes;;;\n"
        "Nombre completo;Cédula;Celular;Fecha de nacimiento;Correo\n"
        "ANDREA TATIANA MERINO ARMIJOS;0105555555;987654321;15/03/1998;andrea@correo.ec\n"
        "erick troya;102030405;0999999999;;\n"
        "Pablo Calva;;;31/02/2000;malo\n"
        ";;;;\n"
    ).encode("cp1252")
    r = await client.post("/api/v1/patients/import/preview", files={"file": ("pacientes.csv", csv, "text/csv")}, headers=h)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["counts"] == {"nuevo": 1, "duplicado": 1, "error": 1}
    andrea = v["rows"][0]["data"]
    assert (andrea["first_name"], andrea["last_name"]) == ("ANDREA TATIANA", "MERINO ARMIJOS")
    assert andrea["phone"] == "0987654321" and andrea["birth_date"] == "1998-03-15"
    assert "cédula" in v["rows"][1]["duplicate"]

    r = await client.post("/api/v1/patients/import", json={"patients": [andrea]}, headers=h)
    assert r.json() == {"created": 1, "skipped": 0}
    # Confirmar dos veces no duplica.
    r = await client.post("/api/v1/patients/import", json={"patients": [andrea]}, headers=h)
    assert r.json() == {"created": 0, "skipped": 1}

    xlsx = _xlsx([["Apellidos", "Nombres", "Teléfono", "Sexo"], ["Abad Girón", "Brayan José", "0991112233", "Masculino"]])
    r = await client.post(
        "/api/v1/patients/import/preview",
        files={"file": ("pacientes.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=h,
    )
    fila = r.json()["rows"][0]
    assert fila["status"] == "nuevo"
    assert fila["data"]["first_name"] == "Brayan José" and fila["data"]["sex"] == "M"

    r = await client.post("/api/v1/patients/import/preview", files={"file": ("x.pdf", b"%PDF", "application/pdf")}, headers=h)
    assert r.status_code == 422
