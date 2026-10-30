"""Clave de acceso de 49 dígitos (que también es el número de autorización)."""

import secrets
from datetime import date


def modulo11(digitos: str) -> str:
    """Dígito verificador: se multiplica de derecha a izquierda por 2..7
    (cíclico), y 11 menos el residuo; 11 → 0 y 10 → 1."""
    total = 0
    factor = 2
    for d in reversed(digitos):
        total += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    verificador = 11 - total % 11
    if verificador == 11:
        return "0"
    if verificador == 10:
        return "1"
    return str(verificador)


def clave_acceso(
    *,
    fecha: date,
    tipo: str,
    ruc: str,
    ambiente: str,
    establecimiento: str,
    punto_emision: str,
    secuencial: int,
    codigo_numerico: str | None = None,
    tipo_emision: str = "1",
) -> str:
    codigo = codigo_numerico or f"{secrets.randbelow(10**8):08d}"
    base = (
        f"{fecha:%d%m%Y}{tipo}{ruc}{ambiente}"
        f"{establecimiento}{punto_emision}{secuencial:09d}{codigo}{tipo_emision}"
    )
    if len(base) != 48 or not base.isdigit():
        raise ValueError("Datos inválidos para la clave de acceso (revise RUC, establecimiento y punto de emisión).")
    return base + modulo11(base)
