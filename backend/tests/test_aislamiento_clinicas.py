"""Aislamiento entre clínicas (multi-inquilino).

La clínica A crea datos en todos los módulos. Luego el administrador de la
clínica B recorre TODAS las rutas de la API que llevan un identificador y
prueba leer, editar, anular y borrar los datos de A. Ninguna debe responder con
éxito, ningún listado de B debe mostrar datos de A, y al final los datos de A
deben estar exactamente igual que antes.
"""
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.main import app
from app.modules.clinics.models import Clinic
from app.modules.users.models import Role, User


async def _login(client, email, password):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _clinica_b(db_session, roles_a):
    """Segunda clínica con su administrador (mismos permisos que el de A)."""
    clinic = Clinic(name="Clínica B")
    db_session.add(clinic)
    await db_session.flush()
    admin_role = roles_a["Administrador"]
    role = Role(clinic_id=clinic.id, name="Administrador", is_system=True, permissions=list(admin_role.permissions))
    db_session.add(role)
    await db_session.flush()
    db_session.add(User(clinic_id=clinic.id, email="admin@clinicab.io", hashed_password=hash_password("AdminB123!"),
                        first_name="Admin", last_name="B", roles=[role]))
    await db_session.commit()


def _png():
    from tests.test_phase7 import _png_bytes
    return _png_bytes()


async def _datos_clinica_a(client, h, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "STORAGE_LOCAL_PATH", str(tmp_path))
    def ok(r):
        assert r.status_code in (200, 201), f"{r.request.method} {r.request.url}: {r.status_code} {r.text}"
        return r.json()
    ids = {}
    p = ok(await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Privada", "national_id": "1700000001"}, headers=h))
    ids["patient_id"] = p["id"]
    pid = p["id"]
    ids["specialty_id"] = ok(await client.post("/api/v1/specialties", json={"name": "Endodoncia A"}, headers=h))["id"]
    ids["professional_id"] = ok(await client.post("/api/v1/professionals", json={"first_name": "Doc", "last_name": "A"}, headers=h))["id"]
    ids["treatment_id"] = ok(await client.post("/api/v1/treatments", json={"name": "Resina A", "default_price": 40}, headers=h))["id"]
    inicio = (datetime.now(timezone.utc) + timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0)
    ids["appointment_id"] = ok(await client.post("/api/v1/appointments", headers=h, json={
        "patient_id": pid, "professional_id": ids["professional_id"],
        "starts_at": inicio.isoformat(), "ends_at": (inicio + timedelta(minutes=30)).isoformat()}))["id"]
    plan = ok(await client.post(f"/api/v1/patients/{pid}/treatment-plans", headers=h, json={
        "title": "Plan A", "items": [{"treatment_id": ids["treatment_id"], "fdi_number": "16", "price": 40}]}))
    ids["plan_id"] = plan["id"]
    ids["plan_item_id"] = plan["items"][0]["id"]
    ids["budget_id"] = ok(await client.post(f"/api/v1/patients/{pid}/budgets", json={"treatment_plan_id": plan["id"]}, headers=h))["id"]
    ids["diagnosis_id"] = ok(await client.post(f"/api/v1/patients/{pid}/diagnoses", json={"description": "Caries A", "fdi_number": "16"}, headers=h))["id"]
    ids["evolution_id"] = ok(await client.post(f"/api/v1/patients/{pid}/evolutions", json={"procedure": "Resina A"}, headers=h))["id"]
    ids["prescription_id"] = ok(await client.post(f"/api/v1/patients/{pid}/prescriptions", headers=h, json={"professional_id": ids["professional_id"],
        "items": [{"medication": "Ibuprofeno 400 mg", "dosage": "1 tableta", "frequency": "cada 8 h", "duration": "3 días"}]}))["id"]
    ids["charge_id"] = ok(await client.post(f"/api/v1/patients/{pid}/charges", json={"description": "Ortodoncia A", "amount": "600"}, headers=h))["id"]
    ids["payment_id"] = ok(await client.post(f"/api/v1/patients/{pid}/payments", json={"amount": "50", "method": "efectivo", "charge_id": ids["charge_id"]}, headers=h))["id"]
    ids["credit_id"] = ok(await client.post(f"/api/v1/patients/{pid}/credits", headers=h, json={
        "charge_id": ids["charge_id"], "installment_count": 3, "frequency": "mensual",
        "first_due_on": (date.today() + timedelta(days=30)).isoformat()}))["id"]
    ids["expense_id"] = ok(await client.post("/api/v1/finance/expenses", headers=h, json={
        "spent_on": date.today().isoformat(), "category": "insumos", "description": "Guantes A", "amount": "20", "method": "efectivo"}))["id"]
    ids["rid"] = ok(await client.post("/api/v1/finance/recurring-expenses", json={"description": "Arriendo A", "category": "arriendo", "amount": "500"}, headers=h))["id"]
    ids["image_id"] = ok(await client.post(f"/api/v1/patients/{pid}/images", files={"file": ("rx.png", _png(), "image/png")},
                                           data={"title": "Periapical A", "image_type": "periapical"}, headers=h))["id"]
    ids["document_id"] = ok(await client.post(f"/api/v1/patients/{pid}/documents", files={"file": ("informe.txt", b"secreto", "text/plain")},
                                              data={"title": "Informe A", "document_type": "informe"}, headers=h))["id"]
    ids["template_id"] = ok(await client.post("/api/v1/consents/templates", json={"name": "Plantilla A", "body": "Texto A"}, headers=h))["id"]
    ids["consent_id"] = ok(await client.post(f"/api/v1/patients/{pid}/consents", json={"template_id": ids["template_id"]}, headers=h))["id"]
    ids["supplier_id"] = ok(await client.post("/api/v1/inventory/suppliers", json={"name": "Proveedor A"}, headers=h))["id"]
    ids["item_id_inv"] = ok(await client.post("/api/v1/inventory/items", json={"name": "Guantes A", "unit": "caja", "minimum_stock": 2}, headers=h))["id"]
    ids["laboratory_id"] = ok(await client.post("/api/v1/laboratory/laboratories", json={"name": "Lab A"}, headers=h))["id"]
    ids["order_id"] = ok(await client.post("/api/v1/laboratory/orders", headers=h, json={
        "patient_id": pid, "laboratory_id": ids["laboratory_id"], "work_type": "corona", "description": "Corona A"}))["id"]
    ids["branch_id"] = ok(await client.post("/api/v1/clinics/branches", json={"name": "Sede A"}, headers=h))["id"]
    ids["operatory_id"] = ok(await client.post("/api/v1/clinics/operatories", json={"branch_id": ids["branch_id"], "name": "Sillón A"}, headers=h))["id"]
    ids["role_id"] = ok(await client.post("/api/v1/roles", json={"name": "Rol A", "permission_codes": ["patients:read"]}, headers=h))["id"]
    ids["request_id"] = ok(await client.post("/api/v1/legal/requests", json={"patient_id": pid, "requester_name": "Ana Privada", "kind": "acceso"}, headers=h))["id"]
    ids["odontogram_id"] = ok(await client.post(f"/api/v1/patients/{pid}/odontogram", headers=h, json={
        "conditions": [{"fdi_number": "16", "surface": "oclusal", "condition": "caries"}]}))["id"]
    ids["access_id"] = ok(await client.post(f"/api/v1/patients/{pid}/portal", json={}, headers=h))["id"]
    me = (await client.get("/api/v1/auth/me", headers=h)).json()
    ids["user_id"] = me["id"]
    return ids


# Qué identificador de A va en cada parámetro de ruta.
def _id_para(param, path, ids):
    if param == "item_id":
        return ids["item_id_inv"] if path.startswith("/api/v1/inventory") else ids["plan_item_id"]
    if param == "record_id":
        return ids["prescription_id"] if "prescriptions" in path else ids["diagnosis_id"]
    return {"periodontogram_id": ids["odontogram_id"], "suggestion_id": ids["evolution_id"]}.get(param, ids.get(param))


# Cuerpos válidos para las escrituras: así el rechazo prueba el aislamiento y no
# una simple validación del formulario.
CUERPOS = [
    (r"/void$|/archive$|/cancel$|/revoke$", {"reason": "intento desde otra clínica"}),
    (r"/patients/\{patient_id\}$", {"first_name": "Hackeado", "last_name": "B"}),
    (r"/patients/\{patient_id\}/payments$", {"amount": "10", "method": "efectivo"}),
    (r"/patients/\{patient_id\}/charges$", {"description": "Cargo B", "amount": "10"}),
    (r"/patients/\{patient_id\}/(evolutions)$", {"procedure": "B"}),
    (r"/patients/\{patient_id\}/diagnoses$", {"description": "B"}),
    (r"/evolutions/\{evolution_id\}$", {"procedure": "Cambiado por B"}),
    (r"/budgets/\{budget_id\}$", {"notes": "B"}),
    (r"/budgets/\{budget_id\}/status$", {"status": "rechazado"}),
    (r"/treatment-plans/\{plan_id\}$", {"title": "Plan B"}),
    (r"/treatment-plans/\{plan_id\}/items/\{item_id\}$", {"status": "cancelado"}),
    (r"/appointments/\{appointment_id\}/status$", {"status": "cancelada", "reason": "B"}),
    (r"/credits/\{credit_id\}/payments$", {"amount": "10", "method": "efectivo"}),
    (r"/consents/\{consent_id\}/sign$", {"signed_by_name": "B"}),
    (r"/(images|documents)/\{\w+\}$", {"title": "Cambiado B", "image_type": "periapical", "document_type": "informe"}),
    (r"/users/\{user_id\}$", {"first_name": "B"}),
    (r"/roles/\{role_id\}$", {"name": "Rol B", "permission_codes": []}),
    (r"/specialties/\{specialty_id\}$", {"name": "B"}),
    (r"/professionals/\{professional_id\}$", {"first_name": "B"}),
    (r"/treatments/\{treatment_id\}$", {"name": "B"}),
    (r"/clinics/(branches|operatories)/\{\w+\}$", {"name": "B"}),
    (r"/inventory/suppliers/\{supplier_id\}$", {"name": "B"}),
    (r"/inventory/items/\{item_id\}$", {"name": "B", "unit": "caja"}),
    (r"/inventory/items/\{item_id\}/movements$", {"movement_type": "salida", "quantity": 1}),
    (r"/laboratory/laboratories/\{laboratory_id\}$", {"name": "B"}),
    (r"/laboratory/orders/\{order_id\}/status$", {"status": "cancelado"}),
    (r"/finance/expenses/\{expense_id\}$", {"spent_on": date.today().isoformat(), "category": "insumos", "description": "B"}),
    (r"/finance/recurring-expenses/\{rid\}$", {"description": "B", "category": "arriendo", "amount": "1"}),
    (r"/legal/requests/\{request_id\}$", {"requester_name": "B", "kind": "acceso"}),
    (r"/patients/\{patient_id\}/portal$", {}),
    (r"/patients/\{patient_id\}/consents$", {"title": "B", "body": "B"}),
]


def _cuerpo(path):
    for patron, cuerpo in CUERPOS:
        if re.search(patron, path):
            return cuerpo
    return {}


async def _foto(client, h, rutas, ids):
    """Estado de todos los recursos de A leídos por A (para comparar después)."""
    foto = {}
    for path in rutas:
        url = path
        for param in re.findall(r"\{(\w+)\}", path):
            url = url.replace("{" + param + "}", str(_id_para(param, path, ids)))
        r = await client.get(url, headers=h)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            foto[path] = r.json()
    return foto


async def test_una_clinica_no_puede_ver_ni_tocar_datos_de_otra(client, clinic_with_users, db_session, tmp_path, monkeypatch):
    ha = await _login(client, "admin@clinicatest.io", "Admin123!")
    ids = await _datos_clinica_a(client, ha, tmp_path, monkeypatch)
    await _clinica_b(db_session, clinic_with_users["roles"])
    hb = await _login(client, "admin@clinicab.io", "AdminB123!")

    # Todas las rutas de la API (según su especificación OpenAPI).
    class _R:
        def __init__(self, path, methods): self.path, self.methods = path, methods
    rutas = [_R(path, {m.upper() for m in ops}) for path, ops in app.openapi()["paths"].items()
             if "{" in path and not path.startswith("/api/v1/portal/view")]
    # Rutas de lectura con identificador que no cambian al leerlas (el registro
    # de accesos a la ficha sí cambia: queda fuera de la comparación).
    lecturas = sorted({r.path for r in rutas if "GET" in r.methods and "access-log" not in r.path and "privacy" not in r.path
                       and "/ai/" not in r.path and not r.path.endswith(".csv") and "download" not in r.path and "/file" not in r.path})
    antes = await _foto(client, ha, lecturas, ids)
    assert len(antes) >= 20, f"La foto de A cubre pocas rutas: {len(antes)}"

    fugas, sin_probar = [], []
    for r in rutas:
        for metodo in sorted(r.methods - {"HEAD", "OPTIONS"}):
            url = r.path
            faltan = False
            for param in re.findall(r"\{(\w+)\}", r.path):
                valor = _id_para(param, r.path, ids)
                if valor is None:
                    faltan = True
                    break
                url = url.replace("{" + param + "}", str(valor))
            if faltan:
                sin_probar.append(f"{metodo} {r.path}")
                continue
            kw = {"headers": hb}
            if metodo in ("POST", "PUT", "PATCH"):
                kw["json"] = _cuerpo(r.path)
            resp = await client.request(metodo, url, **kw)
            if resp.status_code < 400:
                fugas.append(f"{metodo} {r.path} -> {resp.status_code}")
    assert not fugas, "La clínica B accedió a datos de A:\n" + "\n".join(fugas)

    # Ningún listado de B muestra datos de A.
    for url, campo in [("/api/v1/patients", "id"), ("/api/v1/appointments", "id"), ("/api/v1/finance/expenses", "id"),
                       ("/api/v1/finance/portfolio", None), ("/api/v1/inventory/items", "id"), ("/api/v1/laboratory/orders", "id"),
                       ("/api/v1/credits", "id"), ("/api/v1/users", "id"), ("/api/v1/professionals", "id"), ("/api/v1/legal/requests", "id")]:
        r = await client.get(url, headers=hb, params={"from": "2000-01-01T00:00:00Z", "to": "2100-01-01T00:00:00Z"} if "appointments" in url else None)
        assert r.status_code == 200, (url, r.text)
        assert ids["patient_id"] not in r.text and "Privada" not in r.text, f"{url} muestra datos de A"
    busqueda = await client.get("/api/v1/patients", headers=hb, params={"search": "Privada"})
    assert busqueda.json() in ([], {"items": [], "total": 0}) or "Privada" not in busqueda.text

    # Los datos de A quedaron exactamente igual.
    despues = await _foto(client, ha, lecturas, ids)
    cambiados = [p for p in antes if antes[p] != despues.get(p)]
    assert not cambiados, "Datos de A modificados tras los intentos de B: " + ", ".join(cambiados)
    print(f"\nRutas con identificador probadas: {sum(len(r.methods - {'HEAD', 'OPTIONS'}) for r in rutas) - len(sin_probar)}; sin probar: {sin_probar}")


async def test_svg_o_html_disfrazados_de_imagen_no_entran(client, clinic_with_users, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "STORAGE_LOCAL_PATH", str(tmp_path))
    h = await _login(client, "admin@clinicatest.io", "Admin123!")
    pid = (await client.post("/api/v1/patients", json={"first_name": "X", "last_name": "Y"}, headers=h)).json()["id"]
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    for nombre, contenido, tipo in [("a.svg", svg, "image/svg+xml"), ("a.png", b"<html><script>x</script></html>", "image/png")]:
        r = await client.post(f"/api/v1/patients/{pid}/images", files={"file": (nombre, contenido, tipo)},
                              data={"title": "X", "image_type": "periapical"}, headers=h)
        assert r.status_code == 400, (nombre, r.text)
    # Una imagen real entra, y se entrega como contenido inerte.
    ok = await client.post(f"/api/v1/patients/{pid}/images", files={"file": ('rx".png', _png(), "text/html")},
                           data={"title": "Rx", "image_type": "periapical"}, headers=h)
    assert ok.status_code == 201 and ok.json()["mime_type"] == "image/png"
    f = await client.get(f"/api/v1/images/{ok.json()['id']}/file", headers=h)
    assert "sandbox" in f.headers["content-security-policy"] and f.headers["x-content-type-options"] == "nosniff"
    assert '"' not in f.headers["content-disposition"].split('filename="')[1].split('";')[0]


PUBLICAS = {("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/refresh"), ("POST", "/api/v1/auth/logout"),
            ("GET", "/api/v1/health"), ("GET", "/api/v1/portal/view/{token}")}


async def test_sin_sesion_ninguna_ruta_privada_responde(client, clinic_with_users):
    abiertas = []
    for path, ops in app.openapi()["paths"].items():
        for metodo in ops:
            metodo = metodo.upper()
            if (metodo, path) in PUBLICAS:
                continue
            url = re.sub(r"\{\w+\}", "00000000-0000-0000-0000-000000000000", path)
            r = await client.request(metodo, url, json={} if metodo in ("POST", "PUT") else None)
            if r.status_code not in (401, 403):
                abiertas.append(f"{metodo} {path} -> {r.status_code}")
    assert not abiertas, "Rutas que responden sin sesión:\n" + "\n".join(abiertas)


async def test_salud_avisa_si_la_base_no_responde(client, monkeypatch):
    import app.core.database as base

    class Caida:
        async def __aenter__(self):
            raise ConnectionError("sin base")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(base, "async_session_factory", lambda: Caida())
    r = await client.get("/api/v1/health")
    assert r.status_code == 503 and r.json()["status"] == "error"
