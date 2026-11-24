from datetime import date

from tests.sri_falso import SriFalso, preparar_emisor


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _paciente(client, h, nombre="María", apellido="Gómez", cedula="1710034065"):
    r = await client.post("/api/v1/patients", json={"first_name": nombre, "last_name": apellido, "national_id": cedula}, headers=h)
    return r.json()["id"]


async def _cargo(client, h, pid, descripcion, monto):
    return (await client.post(f"/api/v1/patients/{pid}/charges", json={"description": descripcion, "amount": monto}, headers=h)).json()["id"]


async def test_ventas_con_pagos_y_facturas(client, clinic_with_users, monkeypatch):
    SriFalso(monkeypatch)
    h = await _h(client)
    await preparar_emisor(client, h)
    pid = await _paciente(client, h)
    limpieza = await _cargo(client, h, pid, "Limpieza dental", "40")
    resina = await _cargo(client, h, pid, "Resina", "60")
    await client.post(f"/api/v1/patients/{pid}/payments", json={"amount": "40", "method": "transferencia", "reference": "TRX-9", "charge_id": limpieza}, headers=h)
    await client.post(f"/api/v1/patients/{pid}/payments", json={"amount": "20", "method": "efectivo", "charge_id": resina}, headers=h)
    await client.post(f"/api/v1/patients/{pid}/payments", json={"amount": "15", "method": "efectivo"}, headers=h)
    f = (await client.post("/api/v1/invoices", headers=h, json={"patient_id": pid, "items": [{"charge_id": limpieza}]})).json()
    assert f["status"] == "autorizada"

    d = (await client.get("/api/v1/sales", headers=h)).json()
    assert d["facturacion_lista"] is True
    r = d["resumen"]
    assert r["ventas"] == 2 and r["vendido"] == "100.00" and r["cobrado"] == "60.00" and r["pendiente"] == "40.00"
    assert r["facturado"] == "40.00" and r["sin_facturar"] == "60.00" and r["abonos_sin_asignar"] == "15.00"
    por = {v["descripcion"]: v for v in d["items"]}
    lim = por["Limpieza dental"]
    assert lim["estado_pago"] == "pagada" and lim["factura"]["numero"] == f["number"]
    assert lim["facturable"] is False and lim["motivo"].startswith("Ya facturada")
    assert lim["pagos"][0]["referencia"] == "TRX-9" and lim["pagos"][0]["medio"] == "Transferencia bancaria"
    res = por["Resina"]
    assert res["estado_pago"] == "parcial" and res["facturable"] is True and res["factura"] is None

    solo = (await client.get("/api/v1/sales?factura=sin_facturar", headers=h)).json()["items"]
    assert [v["descripcion"] for v in solo] == ["Resina"]
    busca = (await client.get("/api/v1/sales?q=gómez", headers=h)).json()["items"]
    assert len(busca) == 2

    csv = await client.get("/api/v1/sales/export.csv", headers=h)
    assert csv.status_code == 200 and "Limpieza dental" in csv.text and f["number"] in csv.text

    # Anulada con nota de crédito total: la venta vuelve a poder facturarse.
    nc = await client.post(f"/api/v1/invoices/{f['id']}/credit-note", headers=h, json={"reason": "Error en datos"})
    assert nc.status_code == 201, nc.text
    lim = next(v for v in (await client.get("/api/v1/sales", headers=h)).json()["items"] if v["descripcion"] == "Limpieza dental")
    assert lim["facturable"] is True and lim["factura"] is None
    libres = (await client.get(f"/api/v1/patients/{pid}/invoiceable-charges", headers=h)).json()
    assert limpieza in [c["id"] for c in libres]


async def test_ventas_respeta_periodo_y_permisos(client):
    h = await _h(client)
    pid = await _paciente(client, h, "Leo", "Paz", None)
    await _cargo(client, h, pid, "Consulta", "25")
    hoy = date.today().isoformat()
    assert len((await client.get(f"/api/v1/sales?desde={hoy}&hasta={hoy}", headers=h)).json()["items"]) == 1
    assert (await client.get("/api/v1/sales?desde=2000-01-01&hasta=2000-01-31", headers=h)).json()["items"] == []
    d = (await client.get("/api/v1/sales", headers=h)).json()
    assert d["facturacion_lista"] is False and d["faltantes"]
    assert (await client.get("/api/v1/sales")).status_code == 401
