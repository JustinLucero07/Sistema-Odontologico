"""Reglas de contraseña, en un solo sitio para altas, restablecimientos y
cambios propios.

Siguen la línea de NIST SP 800-63B: lo que protege es la longitud y no usar
una contraseña conocida o adivinable, no obligar a símbolos raros que acaban
en un papel pegado al monitor."""

import re
import unicodedata

from fastapi import HTTPException, status

MIN_LENGTH = 8
MAX_LENGTH = 128

# Las que cualquier ataque prueba primero, más las obvias de este producto.
COMMON = {
    "12345678", "123456789", "1234567890", "password", "password1", "password123", "contrasena",
    "contraseña", "qwerty123", "qwertyuiop", "abc12345", "abcd1234", "11111111", "00000000",
    "iloveyou", "admin123", "admin1234", "administrador", "clinica123", "dentista123", "odontologia",
    "odonto123", "ecuador123", "bienvenido", "bienvenido1", "temporal123", "cambiar123", "a1234567",
}


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def problems(password: str, *, email: str = "", names: tuple[str, ...] = ()) -> list[str]:
    """Devuelve por qué no sirve la contraseña; lista vacía si es aceptable."""
    found: list[str] = []
    if len(password) < MIN_LENGTH:
        found.append(f"Debe tener al menos {MIN_LENGTH} caracteres.")
    if len(password) > MAX_LENGTH:
        found.append(f"No puede superar {MAX_LENGTH} caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", password) or not re.search(r"\d", password):
        found.append("Debe combinar letras y números.")
    plain = _plain(password)
    if plain in COMMON or len(set(password)) <= 2:
        found.append("Es una contraseña demasiado común o fácil de adivinar.")
    personal = [_plain(email.split("@")[0])] + [_plain(n) for n in names]
    if any(len(p) >= 4 and p in plain for p in personal):
        found.append("No debe contener su nombre ni su correo.")
    return found


def enforce(password: str, *, email: str = "", names: tuple[str, ...] = ()) -> None:
    found = problems(password, email=email, names=names)
    if found:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=" ".join(found))
