"""Facturación electrónica (SRI, esquema offline) con un SRI simulado."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from cryptography.hazmat.primitives import serialization
from lxml import etree
from signxml import DigestAlgorithm, SignatureConfiguration, SignatureMethod, XMLVerifier

from app.modules.invoicing import sri_client
from app.modules.invoicing.access_key import clave_acceso, modulo11
from app.modules.invoicing.identification import cedula_valida, ruc_valido
from app.modules.invoicing.service import process_due
from tests.sri_falso import CLAVE_P12, RUC_PRUEBA, SriFalso, p12_de_prueba, preparar_emisor


async def _login(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _paciente(client, h, **extra):
    datos = {"first_name": "María", "last_name": "Gómez", "national_id": "1710034065", "email": "maria@correo.ec", **extra}
    r = await client.post("/api/v1/patients", json=datos, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _cargo(client, h, pid, descripcion="Limpieza dental", monto="40"):
    r = await client.post(f"/api/v1/patients/{pid}/charges", json={"description": descripcion, "amount": monto}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _verificar_firma(xml: bytes, cert) -> None:
    cfg = SignatureConfiguration(
        signature_methods=frozenset({SignatureMethod.RSA_SHA1}),
        digest_algorithms=frozenset({DigestAlgorithm.SHA1}),
        expect_references=3,
    )
    XMLVerifier().verify(xml, x509_cert=cert.public_bytes(serialization.Encoding.PEM), expect_config=cfg)


# ------------------------------------------------------------------ Piezas sueltas


def test_modulo11_y_clave_de_acceso():
    # 11 - (suma % 11): 11 → 0 y 10 → 1.
    assert modulo11("0") == "0"
    assert modulo11("1") == "9"
    assert modulo11("5") == "1"
    from datetime import date

    clave = clave_acceso(
        fecha=date(2026, 10, 29), tipo="01", ruc=RUC_PRUEBA, ambiente="1",
        establecimiento="001", punto_emision="002", secuencial=15, codigo_numerico="12345678",
    )
    assert len(clave) == 49
    assert clave[:8] == "29102026" and clave[8:10] == "01" and clave[10:23] == RUC_PRUEBA
    assert clave[23] == "1" and clave[24:30] == "001002" and clave[30:39] == "000000015"
    assert clave[39:47] == "12345678" and clave[47] == "1"
    assert clave[48] == modulo11(clave[:48])


def test_cedula_y_ruc():
    assert cedula_valida("1710034065")
    assert not cedula_valida("1710034066")
    assert not cedula_valida("9910034065")
    assert ruc_valido("1710034065001")
    assert not ruc_valido("1710034065000")
    assert ruc_valido("1790012345001")  # sociedad: lo confirma el SRI


# ------------------------------------------------------------------ Configuración


async def test_configuracion_dice_lo_que_falta_y_valida_la_firma(client, clinic_with_users):
    h = await _login(client)
    r = await client.get("/api/v1/invoicing/settings", headers=h)
    assert r.status_code == 200
    faltan = " ".join(r.json()["missing"])
    assert "RUC" in faltan and "firma" in faltan

    p12, _ = p12_de_prueba()
    mala = await client.post("/api/v1/invoicing/certificate", headers=h,
                             files={"file": ("f.p12", p12, "application/x-pkcs12")}, data={"password": "otra"})
    assert mala.status_code == 422
    assert "clave" in mala.json()["detail"]

    vencida, _ = p12_de_prueba(vence_en_dias=-1)
    r = await client.post("/api/v1/invoicing/certificate", headers=h,
                          files={"file": ("f.p12", vencida, "application/x-pkcs12")}, data={"password": CLAVE_P12})
    assert r.status_code == 422 and "venció" in r.json()["detail"]

    await preparar_emisor(client, h, p12)
    r = await client.get("/api/v1/invoicing/settings", headers=h)
    assert r.json()["missing"] == []
    assert r.json()["has_certificate"] and "CONSULTORIO DE PRUEBA" in r.json()["certificate_subject"]

    # El número inicial se puede fijar (p. ej. si ya facturaba con otro sistema).
    r = await client.put("/api/v1/invoicing/settings", headers=h, json={"next_invoice_number": 120})
    assert r.json()["next_invoice_number"] == 120


async def test_sin_configurar_no_deja_facturar(client, clinic_with_users):
    h = await _login(client)
    r = await client.post("/api/v1/invoices", headers=h, json={"items": [{"description": "Consulta", "unit_price": "20"}]})
    assert r.status_code == 409
    assert "firma" in r.json()["detail"]


# ------------------------------------------------------------------ Emisión


async def test_factura_autorizada_firmada_y_valida(client, clinic_with_users, monkeypatch):
    sri = SriFalso(monkeypatch)
    h = await _login(client)
    p12, cert = p12_de_prueba()
    await preparar_emisor(client, h, p12)
    pid = await _paciente(client, h)
    cargo = await _cargo(client, h, pid, "Limpieza dental", "40")

    r = await client.post("/api/v1/invoices", headers=h, json={
        "patient_id": pid,
        "items": [
            {"charge_id": cargo, "vat_code": "0"},
            # Blanqueamiento: 115 con IVA incluido → base 100 + IVA 15.
            {"description": "Blanqueamiento estético", "unit_price": "115", "vat_code": "4", "price_includes_vat": True},
        ],
        "payment_method": "19",
    })
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["status"] == "autorizada"
    assert f["number"] == "001-001-000000001"
    assert f["buyer_id"] == "1710034065" and f["buyer_id_type"] == "05"
    assert Decimal(f["subtotal"]) == Decimal("140.00")
    assert Decimal(f["vat"]) == Decimal("15.00")
    assert Decimal(f["total"]) == Decimal("155.00")
    assert len(f["access_key"]) == 49

    # Lo que salió hacia el SRI: cumple el XSD oficial y la firma es válida.
    xml = sri.enviados[-1]
    assert sri_client.errores_de_esquema(xml, "01") == []
    _verificar_firma(xml, cert)
    raiz = etree.fromstring(xml)
    assert raiz.findtext("infoFactura/importeTotal") == "155.00"
    assert raiz.findtext("infoFactura/pagos/pago/formaPago") == "19"
    assert [e.text for e in raiz.findall("infoFactura/totalConImpuestos/totalImpuesto/codigoPorcentaje")] == ["0", "4"]

    pdf = await client.get(f"/api/v1/invoices/{f['id']}/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    xml_aut = await client.get(f"/api/v1/invoices/{f['id']}/xml", headers=h)
    assert xml_aut.status_code == 200 and b"<estado>AUTORIZADO</estado>" in xml_aut.content

    # El cargo ya no aparece para facturar y no se puede anular sin nota de crédito.
    libres = (await client.get(f"/api/v1/patients/{pid}/invoiceable-charges", headers=h)).json()
    assert cargo not in [c["id"] for c in libres]
    r = await client.post(f"/api/v1/finance/charges/{cargo}/void", headers=h, json={"reason": "error"})
    assert r.status_code == 409 and "nota de crédito" in r.json()["detail"]
    r = await client.post("/api/v1/invoices", headers=h, json={"patient_id": pid, "items": [{"charge_id": cargo}]})
    assert r.status_code == 409


async def test_numeracion_correlativa(client, clinic_with_users, monkeypatch):
    SriFalso(monkeypatch)
    h = await _login(client)
    await preparar_emisor(client, h)
    numeros = []
    for _ in range(3):
        r = await client.post("/api/v1/invoices", headers=h, json={"items": [{"description": "Consulta", "unit_price": "20"}]})
        assert r.status_code == 201, r.text
        numeros.append(r.json()["number"])
    assert numeros == ["001-001-000000001", "001-001-000000002", "001-001-000000003"]


async def test_consumidor_final_hasta_50(client, clinic_with_users, monkeypatch):
    SriFalso(monkeypatch)
    h = await _login(client)
    await preparar_emisor(client, h)
    ok = await client.post("/api/v1/invoices", headers=h, json={"items": [{"description": "Consulta", "unit_price": "50"}]})
    assert ok.status_code == 201 and ok.json()["buyer_id"] == "9999999999999"
    r = await client.post("/api/v1/invoices", headers=h, json={"items": [{"description": "Corona", "unit_price": "300"}]})
    assert r.status_code == 422 and "consumidor final" in r.json()["detail"]
    r = await client.post("/api/v1/invoices", headers=h, json={
        "buyer": {"id_type": "05", "id_number": "1710034066", "name": "X"}, "items": [{"description": "Corona", "unit_price": "300"}],
    })
    assert r.status_code == 422 and "cédula" in r.json()["detail"]


async def test_sri_caido_se_reintenta(client, clinic_with_users, db_session, monkeypatch):
    sri = SriFalso(monkeypatch)
    sri.caido = True
    h = await _login(client)
    await preparar_emisor(client, h)
    r = await client.post("/api/v1/invoices", headers=h, json={"items": [{"description": "Consulta", "unit_price": "20"}]})
    assert r.status_code == 201
    f = r.json()
    # Queda guardada con su número, pendiente, con el reintento programado.
    assert f["status"] == "pendiente" and f["attempts"] == 1 and f["next_attempt_at"]
    assert "SRI" in f["last_error"]

    sri.caido = False
    from app.modules.invoicing.models import Invoice
    from sqlalchemy import update

    await db_session.execute(update(Invoice).values(next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    assert await process_due(db_session) == 1
    r = await client.get(f"/api/v1/invoices/{f['id']}", headers=h)
    assert r.json()["status"] == "autorizada"


async def test_devuelta_se_descarta_y_libera_el_cargo(client, clinic_with_users, monkeypatch):
    sri = SriFalso(monkeypatch)
    sri.recepcion = "DEVUELTA"
    sri.mensajes = [sri_client.Mensaje("35", "ARCHIVO NO CUMPLE ESTRUCTURA XML", "prueba", "ERROR")]
    h = await _login(client)
    await preparar_emisor(client, h)
    pid = await _paciente(client, h)
    cargo = await _cargo(client, h, pid)
    f = (await client.post("/api/v1/invoices", headers=h, json={"patient_id": pid, "items": [{"charge_id": cargo}]})).json()
    assert f["status"] == "devuelta"
    assert f["sri_messages"][0]["mensaje"] == "ARCHIVO NO CUMPLE ESTRUCTURA XML"

    # Reenviar tras corregir: misma clave de acceso.
    sri.recepcion = "RECIBIDA"
    r = await client.post(f"/api/v1/invoices/{f['id']}/retry", headers=h)
    assert r.json()["status"] == "autorizada" and r.json()["access_key"] == f["access_key"]

    # Otra devuelta que se descarta: el cargo vuelve a quedar libre.
    cargo2 = await _cargo(client, h, pid, "Resina", "35")
    sri.recepcion = "DEVUELTA"
    f2 = (await client.post("/api/v1/invoices", headers=h, json={"patient_id": pid, "items": [{"charge_id": cargo2}]})).json()
    r = await client.post(f"/api/v1/invoices/{f2['id']}/discard", headers=h, json={"reason": "Datos del comprador errados"})
    assert r.json()["status"] == "descartada"
    libres = (await client.get(f"/api/v1/patients/{pid}/invoiceable-charges", headers=h)).json()
    assert cargo2 in [c["id"] for c in libres]
    # Una autorizada no se descarta: se anula con nota de crédito.
    r = await client.post(f"/api/v1/invoices/{f['id']}/discard", headers=h, json={"reason": "x" * 5})
    assert r.status_code == 409


async def test_nota_de_credito_total_y_parcial(client, clinic_with_users, monkeypatch):
    sri = SriFalso(monkeypatch)
    h = await _login(client)
    p12, cert = p12_de_prueba()
    await preparar_emisor(client, h, p12)
    pid = await _paciente(client, h)
    cargo = await _cargo(client, h, pid, "Endodoncia", "180")
    f = (await client.post("/api/v1/invoices", headers=h, json={"patient_id": pid, "items": [{"charge_id": cargo}]})).json()
    assert f["status"] == "autorizada"

    parcial = await client.post(f"/api/v1/invoices/{f['id']}/credit-note", headers=h, json={"reason": "Descuento acordado", "amount": "30"})
    assert parcial.status_code == 201, parcial.text
    nc = parcial.json()
    assert nc["doc_type"] == "04" and nc["status"] == "autorizada" and Decimal(nc["total"]) == Decimal("30.00")
    assert nc["number"] == "001-001-000000001"  # numeración propia de notas de crédito
    xml = sri.enviados[-1]
    assert sri_client.errores_de_esquema(xml, "04") == []
    _verificar_firma(xml, cert)
    assert etree.fromstring(xml).findtext("infoNotaCredito/numDocModificado") == f["number"]

    r = await client.get(f"/api/v1/invoices/{f['id']}", headers=h)
    assert Decimal(r.json()["credited"]) == Decimal("30.00")
    # Ya no se puede la total ni pasarse del saldo.
    assert (await client.post(f"/api/v1/invoices/{f['id']}/credit-note", headers=h, json={"reason": "Anular"})).status_code == 409
    assert (await client.post(f"/api/v1/invoices/{f['id']}/credit-note", headers=h, json={"reason": "Más", "amount": "151"})).status_code == 422
    r = await client.post(f"/api/v1/invoices/{f['id']}/credit-note", headers=h, json={"reason": "Resto", "amount": "150"})
    assert r.status_code == 201
    pdf = await client.get(f"/api/v1/invoices/{r.json()['id']}/pdf", headers=h)
    assert pdf.content[:4] == b"%PDF"


async def test_no_autorizada_muestra_el_motivo(client, clinic_with_users, monkeypatch):
    sri = SriFalso(monkeypatch)
    sri.autorizacion = "NO AUTORIZADO"
    sri.mensajes = [sri_client.Mensaje("39", "FIRMA INVALIDA", "", "ERROR")]
    h = await _login(client)
    await preparar_emisor(client, h)
    f = (await client.post("/api/v1/invoices", headers=h, json={"items": [{"description": "Consulta", "unit_price": "20"}]})).json()
    assert f["status"] == "no_autorizada"
    assert f["sri_messages"][0]["mensaje"] == "FIRMA INVALIDA"


async def test_quien_no_tiene_permiso_no_factura(client, clinic_with_users, monkeypatch):
    SriFalso(monkeypatch)
    h = await _login(client)
    await preparar_emisor(client, h)
    hd = await _login(client, "dentist@clinicatest.io", "Dentist123!")
    r = await client.post("/api/v1/invoices", headers=hd, json={"items": [{"description": "Consulta", "unit_price": "20"}]})
    assert r.status_code == 403
    assert (await client.post("/api/v1/invoicing/certificate", headers=hd, files={"file": ("f.p12", b"x")}, data={"password": "x"})).status_code == 403
