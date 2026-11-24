import re
import unicodedata

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, require_permission
from app.modules.odontogram.constants import VALID_FDI_NUMBERS

PIEZA_COMPLETA = {
    "corona", "puente", "implante", "ausente", "extraccion_indicada", "extraccion_realizada",
    "endodoncia", "protesis", "movilidad", "diente_retenido",
}

# Frases → condición (se buscan de la más larga a la más corta).
CONDICIONES: dict[str, str] = {
    "restauracion defectuosa": "restauracion_defectuosa",
    "resina defectuosa": "restauracion_defectuosa",
    "obturacion defectuosa": "restauracion_defectuosa",
    "restauracion filtrada": "restauracion_defectuosa",
    "filtrada": "restauracion_defectuosa",
    "tratamiento de conducto": "endodoncia",
    "extraccion indicada": "extraccion_indicada",
    "para extraer": "extraccion_indicada",
    "por extraer": "extraccion_indicada",
    "extraer": "extraccion_indicada",
    "extraccion realizada": "extraccion_realizada",
    "extraido": "extraccion_realizada",
    "extraida": "extraccion_realizada",
    "tratamiento pendiente": "tratamiento_pendiente",
    "pendiente": "tratamiento_pendiente",
    "tratamiento realizado": "tratamiento_realizado",
    "realizado": "tratamiento_realizado",
    "diente retenido": "diente_retenido",
    "retenido": "diente_retenido",
    "incluido": "diente_retenido",
    "se mueve": "movilidad",
    "movilidad": "movilidad",
    "caries": "caries",
    "carie": "caries",
    "restauracion": "restauracion",
    "restaurado": "restauracion",
    "resina": "restauracion",
    "obturacion": "restauracion",
    "obturado": "restauracion",
    "amalgama": "restauracion",
    "corona": "corona",
    "puente": "puente",
    "implante": "implante",
    "ausente": "ausente",
    "falta": "ausente",
    "no esta": "ausente",
    "endodoncia": "endodoncia",
    "conducto": "endodoncia",
    "fractura": "fractura",
    "fracturado": "fractura",
    "fracturada": "fractura",
    "roto": "fractura",
    "rota": "fractura",
    "sellante": "sellante",
    "sellador": "sellante",
    "protesis": "protesis",
    "sano": "sano",
    "sana": "sano",
    "borrar": "sano",
}

CARAS: dict[str, str] = {
    "oclusal": "oclusal", "incisal": "oclusal",
    "mesial": "mesial", "distal": "distal",
    "vestibular": "vestibular", "bucal": "vestibular", "labial": "vestibular",
    "lingual": "lingual", "palatino": "lingual", "palatina": "lingual",
}
# Abreviaturas clínicas: «MOD» = mesial, oclusal y distal.
SIGLAS = {"m": "mesial", "o": "oclusal", "d": "distal", "v": "vestibular", "l": "lingual", "p": "lingual"}
SIGLAS_VALIDAS = ["modvl", "modv", "modl", "modp", "mod", "mo", "om", "od", "mv", "dv", "ml", "dl", "mp", "dp"]

UNIDADES = {
    "uno": 1, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
}
ESPECIALES = {
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21,
    "veintiun": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80}


class Hallazgo(BaseModel):
    fdi_number: str
    surface: str
    condition: str


class DictadoIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class DictadoOut(BaseModel):
    hallazgos: list[Hallazgo]
    sin_entender: list[str]


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9,.;\n -]", " ", t)
    return re.sub(r"[ \t]+", " ", t)


def _numeros_en_palabras(t: str) -> str:
    """«treinta y seis» → «36», «once» → «11», «tres seis» → «36»."""
    for d, v in DECENAS.items():
        for u, n in UNIDADES.items():
            t = re.sub(rf"\b{d} y {u}\b", str(v + n), t)
        t = re.sub(rf"\b{d}\b", str(v), t)
    for p, v in sorted(ESPECIALES.items(), key=lambda x: -len(x[0])):
        t = re.sub(rf"\b{p}\b", str(v), t)
    # Dos cifras dichas por separado: «tres seis» o «3 6» → «36».
    u = "|".join(UNIDADES)
    t = re.sub(rf"\b({u}|[1-8])\s+({u}|[1-8])\b(?!\s*y\b)", lambda m: f"{_digito(m.group(1))}{_digito(m.group(2))}", t)
    return t


def _digito(p: str) -> str:
    return p if p.isdigit() else str(UNIDADES[p])


def interpretar(texto: str) -> DictadoOut:
    t = _numeros_en_palabras(_normalizar(texto))
    hallazgos: list[Hallazgo] = []
    sin_entender: list[str] = []
    vistos: set[tuple[str, str, str]] = set()
    frases = sorted(CONDICIONES, key=len, reverse=True)
    for trozo in re.split(r"[,.;\n]|\bsiguiente\b|\bluego\b", t):
        trozo = trozo.strip()
        if not trozo:
            continue
        piezas = [p for p in re.findall(r"\b(\d{2})\b", trozo) if p in VALID_FDI_NUMBERS]
        condicion = None
        resto = f" {trozo} "
        for f in frases:
            if re.search(rf"\b{f}\b", resto):
                condicion = CONDICIONES[f]
                resto = re.sub(rf"\b{f}\b", " ", resto)
                break
        caras = [CARAS[c] for c in re.findall(r"\b(" + "|".join(CARAS) + r")\b", resto)]
        # «mesio oclusal», «mesio-ocluso-distal»
        for pref, cara in (("mesio", "mesial"), ("disto", "distal"), ("ocluso", "oclusal"), ("vestibulo", "vestibular"), ("linguo", "lingual")):
            if re.search(rf"\b{pref}\b", resto):
                caras.append(cara)
        for sigla in re.findall(r"\b(" + "|".join(SIGLAS_VALIDAS) + r")\b", resto):
            caras.extend(SIGLAS[c] for c in sigla)
        if not piezas or not condicion:
            if re.search(r"[a-z0-9]", trozo):
                sin_entender.append(trozo)
            continue
        if condicion in PIEZA_COMPLETA or not caras:
            superficies = ["whole"]
        else:
            superficies = list(dict.fromkeys(caras))
        for p in piezas:
            for s in superficies:
                clave = (p, s, condicion)
                if clave not in vistos:
                    vistos.add(clave)
                    hallazgos.append(Hallazgo(fdi_number=p, surface=s, condition=condicion))
    return DictadoOut(hallazgos=hallazgos, sin_entender=sin_entender)


router = APIRouter(prefix="/api/v1/odontogram", tags=["odontogram"])


@router.post("/dictation", response_model=DictadoOut)
async def post_dictado(
    payload: DictadoIn,
    current_user: CurrentUser = Depends(require_permission("odontogram:write")),
):
    return interpretar(payload.texto)
