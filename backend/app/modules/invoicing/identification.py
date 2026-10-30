"""Validación de cédula y RUC ecuatorianos, para rechazar un dígito mal
escrito antes de que lo haga el SRI."""

from app.modules.invoicing.constants import (
    CONSUMIDOR_FINAL_ID,
    ID_CEDULA,
    ID_CONSUMIDOR_FINAL,
    ID_RUC,
)


def cedula_valida(cedula: str) -> bool:
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    provincia = int(cedula[:2])
    if not (1 <= provincia <= 24 or provincia == 30) or int(cedula[2]) >= 6:
        return False
    total = 0
    for i, d in enumerate(cedula[:9]):
        v = int(d) * (2 if i % 2 == 0 else 1)
        total += v - 9 if v > 9 else v
    return (10 - total % 10) % 10 == int(cedula[9])


def ruc_valido(ruc: str) -> bool:
    """Estructura del RUC: 13 dígitos, provincia válida y terminado en
    establecimiento distinto de 000. El dígito verificador de sociedades y
    entidades públicas tiene casos especiales, así que no se exige aquí: lo
    confirma el SRI."""
    if len(ruc) != 13 or not ruc.isdigit() or ruc[10:] == "000":
        return False
    provincia = int(ruc[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False
    if int(ruc[2]) < 6:  # persona natural: su base es una cédula
        return cedula_valida(ruc[:10])
    return ruc[2] in "69"


def error_identificacion(tipo: str, numero: str) -> str | None:
    if tipo == ID_CONSUMIDOR_FINAL:
        return None if numero == CONSUMIDOR_FINAL_ID else "Consumidor final se identifica con 9999999999999."
    if tipo == ID_CEDULA and not cedula_valida(numero):
        return "La cédula no es válida: revise los 10 dígitos."
    if tipo == ID_RUC and not ruc_valido(numero):
        return "El RUC no es válido: revise los 13 dígitos."
    if not numero.strip():
        return "Falta la identificación del comprador."
    return None
