"""Importar pacientes desde Excel (.xlsx) o CSV, con vista previa.

Dos pasos a propósito: primero se lee el archivo y se muestra qué se va a
crear, qué está repetido y qué tiene errores; recién al confirmar se guarda.
Así nadie mete 999 pacientes mal partidos sin darse cuenta.

El .xlsx se lee con la librería estándar (es un ZIP con XML): no hace falta
instalar nada más en el servidor."""

import csv
import io
import re
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000

# Campo del paciente ← encabezados que se reconocen (ya normalizados).
SINONIMOS: dict[str, list[str]] = {
    "full_name": ["nombre completo", "nombres y apellidos", "nombre y apellido", "apellidos y nombres",
                  "paciente", "nombre del paciente", "cliente", "razon social"],
    "first_name": ["nombres", "nombre", "primer nombre", "first name", "nombres del paciente"],
    "last_name": ["apellidos", "apellido", "last name", "apellidos del paciente"],
    "national_id": ["cedula", "ci", "c i", "identificacion", "documento", "dni", "ruc", "pasaporte",
                    "cedula ruc", "numero de cedula", "no cedula", "n cedula", "cedula de identidad"],
    "birth_date": ["fecha de nacimiento", "nacimiento", "fecha nacimiento", "f nacimiento", "fnac",
                   "fecha nac", "cumpleanos"],
    "sex": ["sexo", "genero"],
    "phone": ["telefono", "celular", "movil", "telefono celular", "tel", "telefono 1", "numero de telefono",
              "contacto", "telefono movil"],
    "whatsapp": ["whatsapp", "wsp", "whats app"],
    "email": ["correo", "email", "e mail", "correo electronico", "mail"],
    "address": ["direccion", "domicilio", "direccion domicilio"],
    "city": ["ciudad", "canton", "localidad"],
    "occupation": ["ocupacion", "profesion", "trabajo"],
    "emergency_contact_name": ["contacto de emergencia", "nombre contacto emergencia", "emergencia"],
    "emergency_contact_phone": ["telefono de emergencia", "telefono emergencia", "tel emergencia"],
    "notes": ["notas", "observaciones", "observacion", "comentarios", "nota"],
}
CAMPOS = list(SINONIMOS)
ETIQUETAS = {
    "full_name": "Nombre completo", "first_name": "Nombres", "last_name": "Apellidos", "national_id": "Cédula",
    "birth_date": "Fecha de nacimiento", "sex": "Sexo", "phone": "Teléfono", "whatsapp": "WhatsApp",
    "email": "Correo", "address": "Dirección", "city": "Ciudad", "occupation": "Ocupación",
    "emergency_contact_name": "Contacto de emergencia", "emergency_contact_phone": "Teléfono de emergencia",
    "notes": "Notas",
}
LIMITES = {"first_name": 150, "last_name": 150, "national_id": 50, "phone": 50, "whatsapp": 50, "email": 255,
           "address": 300, "city": 120, "occupation": 150, "emergency_contact_name": 200,
           "emergency_contact_phone": 50}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ArchivoInvalido(ValueError):
    pass


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def detectar_columnas(encabezados: list[str]) -> dict[str, str | None]:
    """encabezado original → campo (o None si no se reconoce)."""
    usados: set[str] = set()
    out: dict[str, str | None] = {}
    for h in encabezados:
        n = normalizar(h)
        campo = None
        for c, sin in SINONIMOS.items():
            if c in usados:
                continue
            if n in sin or n == c.replace("_", " "):
                campo = c
                break
        if campo is None:
            for c, sin in SINONIMOS.items():
                if c not in usados and n and any(n.startswith(s) for s in sin if len(s) > 4):
                    campo = c
                    break
        if campo:
            usados.add(campo)
        out[h] = campo
    return out


# ---- Lectura de archivos ---------------------------------------------------


def _leer_csv(datos: bytes) -> list[list[str]]:
    for cod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = datos.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    muestra = texto[:4096]
    delim = max([";", ",", "\t", "|"], key=muestra.count)
    return [fila for fila in csv.reader(io.StringIO(texto), delimiter=delim)]


_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _leer_xlsx(datos: bytes) -> list[list[str]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile as e:
        raise ArchivoInvalido("El archivo no es un Excel válido (.xlsx).") from e
    nombres = set(z.namelist())
    compartidas: list[str] = []
    if "xl/sharedStrings.xml" in nombres:
        raiz = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
        for si in raiz.findall("m:si", _NS):
            compartidas.append("".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")))
    # Primera hoja según el libro (no siempre es sheet1.xml).
    hoja = "xl/worksheets/sheet1.xml"
    try:
        libro = ElementTree.fromstring(z.read("xl/workbook.xml"))
        primera = libro.find("m:sheets/m:sheet", _NS)
        rels = ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = primera.get(_REL) if primera is not None else None
        for r in rels:
            if r.get("Id") == rid:
                destino = r.get("Target").lstrip("/")
                hoja = destino if destino.startswith("xl/") else f"xl/{destino}"
    except (KeyError, ElementTree.ParseError, AttributeError):
        pass
    if hoja not in nombres:
        raise ArchivoInvalido("No se encontró ninguna hoja en el Excel.")
    # Estilos de fecha: celdas numéricas con formato de fecha → fecha.
    fechas_estilo: set[int] = set()
    if "xl/styles.xml" in nombres:
        est = ElementTree.fromstring(z.read("xl/styles.xml"))
        formatos_fecha = {14, 15, 16, 17, 22, 27, 30, 36, 50, 57}
        for nf in est.findall("m:numFmts/m:numFmt", _NS):
            codigo = (nf.get("formatCode") or "").lower()
            if any(x in codigo for x in ("yy", "dd", "mm/", "/mm")) and "h" not in codigo.replace("ch", ""):
                formatos_fecha.add(int(nf.get("numFmtId")))
        xfs = est.find("m:cellXfs", _NS)
        if xfs is not None:
            for i, xf in enumerate(xfs.findall("m:xf", _NS)):
                if int(xf.get("numFmtId", 0)) in formatos_fecha:
                    fechas_estilo.add(i)
    raiz = ElementTree.fromstring(z.read(hoja))
    filas: list[list[str]] = []
    for row in raiz.iter(f"{{{_NS['m']}}}row"):
        valores: dict[int, str] = {}
        for c in row.findall("m:c", _NS):
            ref = c.get("r") or ""
            idx = _col(ref) if ref else len(valores)
            tipo = c.get("t")
            v = c.find("m:v", _NS)
            if tipo == "s" and v is not None:
                texto = compartidas[int(v.text)] if v.text and int(v.text) < len(compartidas) else ""
            elif tipo == "inlineStr":
                texto = "".join(t.text or "" for t in c.iter(f"{{{_NS['m']}}}t"))
            elif v is not None and v.text is not None:
                texto = v.text
                if int(c.get("s", -1)) in fechas_estilo:
                    try:
                        texto = (date(1899, 12, 30) + timedelta(days=int(float(texto)))).isoformat()
                    except (ValueError, OverflowError):
                        pass
                elif re.fullmatch(r"-?\d+\.0+", texto):
                    texto = texto.split(".")[0]
                elif re.fullmatch(r"\d+(\.\d+)?E\+?\d+", texto, re.I):
                    texto = str(int(float(texto)))
            else:
                texto = ""
            valores[idx] = texto
        if valores:
            filas.append([valores.get(i, "") for i in range(max(valores) + 1)])
        if len(filas) > MAX_ROWS + 1:
            break
    return filas


def leer_archivo(nombre: str, datos: bytes) -> tuple[list[str], list[list[str]]]:
    if len(datos) > MAX_BYTES:
        raise ArchivoInvalido("El archivo supera los 5 MB.")
    ext = (nombre or "").lower().rsplit(".", 1)[-1]
    if ext == "xlsx" or datos[:2] == b"PK":
        filas = _leer_xlsx(datos)
    elif ext in ("csv", "txt"):
        filas = _leer_csv(datos)
    elif ext == "xls":
        raise ArchivoInvalido("El formato .xls antiguo no se puede leer: ábralo en Excel y guárdelo como .xlsx o .csv.")
    else:
        raise ArchivoInvalido("Formato no soportado: use un archivo .xlsx o .csv.")
    filas = [[(c or "").strip() for c in f] for f in filas]
    filas = [f for f in filas if any(f)]
    if not filas:
        raise ArchivoInvalido("El archivo está vacío.")
    # El encabezado es la primera fila que tenga al menos 2 columnas reconocibles
    # (hay planillas con un título arriba).
    for i, fila in enumerate(filas[:10]):
        if sum(1 for v in detectar_columnas(fila).values() if v) >= 2:
            encabezados = fila
            cuerpo = filas[i + 1:]
            break
    else:
        encabezados, cuerpo = filas[0], filas[1:]
    if len(cuerpo) > MAX_ROWS:
        raise ArchivoInvalido(f"Máximo {MAX_ROWS} pacientes por archivo. Divídalo en varias partes.")
    ancho = len(encabezados)
    encabezados = [h or f"Columna {i + 1}" for i, h in enumerate(encabezados)]
    cuerpo = [(f + [""] * ancho)[:ancho] for f in cuerpo]
    return encabezados, cuerpo


# ---- Conversión de valores -------------------------------------------------


def _fecha(v: str) -> date | None:
    v = (v or "").strip()
    if not v:
        return None
    if re.fullmatch(r"\d{4,5}", v):  # número de serie de Excel
        try:
            return date(1899, 12, 30) + timedelta(days=int(v))
        except OverflowError:
            return None
    v = v.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            d = datetime.strptime(v, fmt).date()
            if d.year < 1900:
                return None
            return d
        except ValueError:
            continue
    raise ValueError(f"Fecha no reconocida: «{v}»")


def _sexo(v: str) -> str | None:
    n = normalizar(v)
    if not n:
        return None
    if n in ("m", "masculino", "hombre", "h", "male", "varon"):
        return "M"
    if n in ("f", "femenino", "mujer", "female"):
        return "F"
    return "O"


def _titulo(v: str) -> str:
    """«MERINO ARMIJOS» se respeta; «merino armijos» pasa a «Merino Armijos»."""
    v = re.sub(r"\s+", " ", v or "").strip()
    return v.title() if v and v == v.lower() else v


def _partir_nombre(completo: str, orden: str) -> tuple[str, str]:
    """Parte un nombre completo en (nombres, apellidos).

    2 palabras: 1 + 1. 3 palabras: 1 nombre y 2 apellidos. 4 o más: dos
    apellidos y el resto nombres. `orden` dice qué va primero en el archivo."""
    partes = _titulo(completo).split()
    if len(partes) == 1:
        return partes[0], ""
    n_apellidos = 1 if len(partes) == 2 else 2
    if orden == "apellidos_nombres":
        return " ".join(partes[n_apellidos:]), " ".join(partes[:n_apellidos])
    return " ".join(partes[:-n_apellidos]), " ".join(partes[-n_apellidos:])


def convertir_fila(valores: dict[str, str], orden: str) -> tuple[dict, list[str]]:
    """Devuelve (datos del paciente, errores)."""
    errores: list[str] = []
    d: dict = {}
    nombres = _titulo(valores.get("first_name", ""))
    apellidos = _titulo(valores.get("last_name", ""))
    if valores.get("full_name") and not (nombres and apellidos):
        n, a = _partir_nombre(valores["full_name"], orden)
        nombres = nombres or n
        apellidos = apellidos or a
    if not nombres:
        errores.append("Falta el nombre")
    if not apellidos:
        errores.append("Falta el apellido")
    d["first_name"] = nombres
    d["last_name"] = apellidos
    for campo in ("national_id", "phone", "whatsapp", "address", "city", "occupation",
                  "emergency_contact_name", "emergency_contact_phone", "notes"):
        v = re.sub(r"\s+", " ", valores.get(campo, "") or "").strip()
        if v and campo in ("phone", "whatsapp", "emergency_contact_phone"):
            v = re.sub(r"[^\d+]", "", v) or v
            # Excel se come el 0 inicial de los celulares: 987654321 → 0987654321
            if re.fullmatch(r"9\d{8}", v):
                v = "0" + v
        if v and campo == "national_id":
            v = re.sub(r"[\s.-]", "", v)
            if re.fullmatch(r"\d{9}", v):
                v = "0" + v
        if v and campo in LIMITES:
            v = v[: LIMITES[campo]]
        d[campo] = v or None
    correo = (valores.get("email") or "").strip().lower()
    if correo and not _EMAIL.match(correo):
        errores.append(f"Correo no válido: «{correo}»")
        correo = ""
    d["email"] = correo or None
    try:
        d["birth_date"] = _fecha(valores.get("birth_date", ""))
        if d["birth_date"] and d["birth_date"] > date.today():
            errores.append("La fecha de nacimiento es futura")
            d["birth_date"] = None
    except ValueError as e:
        errores.append(str(e))
        d["birth_date"] = None
    d["sex"] = _sexo(valores.get("sex", ""))
    return d, errores


# ---- Vista previa y guardado -------------------------------------------------


def _clave_nombre(nombres: str, apellidos: str) -> str:
    return normalizar(f"{nombres} {apellidos}")


async def _existentes(db, clinic_id) -> tuple[set[str], set[str]]:
    from sqlalchemy import select

    from app.modules.patients.models import Patient

    filas = (
        await db.execute(
            select(Patient.national_id, Patient.first_name, Patient.last_name).where(
                Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)
            )
        )
    ).all()
    cedulas = {re.sub(r"[\s.-]", "", c) for c, _, _ in filas if c}
    nombres = {_clave_nombre(n, a) for _, n, a in filas}
    return cedulas, nombres


async def analizar(db, clinic_id, encabezados, cuerpo, mapeo: dict[str, str | None], orden: str) -> dict:
    cedulas, nombres = await _existentes(db, clinic_id)
    vistos_ced: dict[str, int] = {}
    vistos_nom: dict[str, int] = {}
    filas = []
    cuentas = {"nuevo": 0, "duplicado": 0, "error": 0}
    for i, fila in enumerate(cuerpo, start=1):
        valores: dict[str, str] = {}
        for h, v in zip(encabezados, fila):
            campo = mapeo.get(h)
            if campo and v and not valores.get(campo):
                valores[campo] = v
        if not any(valores.values()):
            continue
        datos, errores = convertir_fila(valores, orden)
        duplicado = None
        ced = datos.get("national_id")
        clave = _clave_nombre(datos["first_name"], datos["last_name"])
        if not errores:
            if ced and ced in cedulas:
                duplicado = f"Ya existe un paciente con la cédula {ced}"
            elif clave in nombres:
                duplicado = "Ya existe un paciente con ese nombre"
            elif ced and ced in vistos_ced:
                duplicado = f"Repetido en el archivo (fila {vistos_ced[ced]})"
            elif clave in vistos_nom and not ced:
                duplicado = f"Repetido en el archivo (fila {vistos_nom[clave]})"
        if ced:
            vistos_ced.setdefault(ced, i)
        vistos_nom.setdefault(clave, i)
        estado = "error" if errores else ("duplicado" if duplicado else "nuevo")
        cuentas[estado] += 1
        filas.append({
            "row": i, "status": estado, "errors": errores, "duplicate": duplicado,
            "data": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in datos.items()},
        })
    return {
        "headers": encabezados,
        "mapping": mapeo,
        "fields": [{"code": c, "label": ETIQUETAS[c]} for c in CAMPOS],
        "rows": filas,
        "counts": cuentas,
    }


async def guardar(db, clinic_id, actor_id, pacientes: list, omitir_duplicados: bool = True) -> dict:
    """Crea los pacientes confirmados. Vuelve a revisar repetidos por si
    alguien creó el mismo paciente mientras se revisaba la vista previa."""
    from app.core.audit import record_audit
    from app.modules.patients.models import Patient

    cedulas, nombres = await _existentes(db, clinic_id)
    creados = omitidos = 0
    for p in pacientes:
        datos = p.model_dump()
        ced = datos.get("national_id")
        clave = _clave_nombre(datos["first_name"], datos["last_name"])
        if omitir_duplicados and ((ced and ced in cedulas) or clave in nombres):
            omitidos += 1
            continue
        db.add(Patient(clinic_id=clinic_id, **datos))
        if ced:
            cedulas.add(ced)
        nombres.add(clave)
        creados += 1
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="import", entity_type="patient", entity_id=None,
        after={"creados": creados, "omitidos": omitidos},
    )
    return {"created": creados, "skipped": omitidos}
