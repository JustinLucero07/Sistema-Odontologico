"""Archivos que suben los usuarios: qué son de verdad y cómo se entregan.

El tipo que declara el navegador no es confiable (lo escribe quien sube el
archivo), así que las imágenes se reconocen por sus primeros bytes. Y todo
archivo se entrega con cabeceras que impiden que el navegador lo ejecute como
página: un SVG o un HTML con código no puede correr en el dominio del sistema.
"""
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
    """Content-Disposition sin inyección de cabeceras, y una política que
    convierte el archivo en contenido inerte aunque alguien lo abra directo."""
    disposicion = "inline" if en_linea else "attachment"
    return {
        "Content-Disposition": f"{disposicion}; filename=\"{_nombre_seguro(nombre)}\"; filename*=UTF-8''{quote(nombre or 'archivo')}",
        "Content-Security-Policy": "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox",
        "X-Content-Type-Options": "nosniff",
    }
