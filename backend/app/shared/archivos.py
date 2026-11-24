import re
import unicodedata
from urllib.parse import quote

_FIRMAS = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
]


def tipo_de_imagen(contenido: bytes) -> str | None:
    """El tipo real de la imagen, o None si no es una imagen de mapa de bits."""
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    for firma, tipo in _FIRMAS:
        if contenido.startswith(firma):
            return tipo
    return None


def _nombre_seguro(nombre: str | None) -> str:
    nombre = unicodedata.normalize("NFKD", nombre or "archivo").encode("ascii", "ignore").decode()
    nombre = re.sub(r'[^A-Za-z0-9._ -]', "_", nombre).strip() or "archivo"
    return nombre[:120]


def cabeceras_archivo(nombre: str | None, en_linea: bool) -> dict[str, str]:
    disposicion = "inline" if en_linea else "attachment"
    return {
        "Content-Disposition": f"{disposicion}; filename=\"{_nombre_seguro(nombre)}\"; filename*=UTF-8''{quote(nombre or 'archivo')}",
        "Content-Security-Policy": "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox",
        "X-Content-Type-Options": "nosniff",
    }
