"""Cifrado de la firma electrónica guardada.

La llave sale de CERT_ENCRYPTION_KEY si está configurada y, si no, se deriva
de JWT_SECRET_KEY. OJO: si se cambia esa clave, las firmas guardadas dejan de
poder leerse y cada consulta tendrá que volver a subir su .p12."""

import base64
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate, ExtensionNotFound, KeyUsage

from app.core.config import get_settings


def _fernet() -> Fernet:
    s = get_settings()
    if s.CERT_ENCRYPTION_KEY:
        return Fernet(s.CERT_ENCRYPTION_KEY.encode())
    llave = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"odonto-firma-sri", info=b"p12").derive(
        s.JWT_SECRET_KEY.encode()
    )
    return Fernet(base64.urlsafe_b64encode(llave))


def cifrar(datos: bytes) -> bytes:
    return _fernet().encrypt(datos)


def descifrar(datos: bytes) -> bytes:
    try:
        return _fernet().decrypt(datos)
    except InvalidToken as e:
        raise ValueError(
            "No se pudo leer la firma guardada (cambió la llave del servidor). Vuelva a subir el archivo .p12."
        ) from e


class FirmaInvalida(ValueError):
    pass


def abrir_p12(contenido: bytes, clave: str) -> tuple[RSAPrivateKey, Certificate]:
    """Abre el .p12 y devuelve la llave privada y SU certificado (el que la
    acompaña, no los de la cadena de la entidad emisora)."""
    try:
        llave, certificado, _ = pkcs12.load_key_and_certificates(contenido, clave.encode())
    except ValueError as e:
        raise FirmaInvalida("La clave de la firma no es correcta o el archivo no es un .p12 válido.") from e
    if llave is None or certificado is None:
        raise FirmaInvalida("El archivo no contiene una llave privada con su certificado.")
    if not isinstance(llave, RSAPrivateKey):
        raise FirmaInvalida("La firma debe ser RSA, que es la que acepta el SRI.")
    try:
        uso = certificado.extensions.get_extension_for_class(KeyUsage).value
        if not (uso.digital_signature or uso.content_commitment):
            raise FirmaInvalida("El certificado del archivo no sirve para firmar.")
    except ExtensionNotFound:
        pass
    return llave, certificado


def vigente(certificado: Certificate) -> bool:
    ahora = datetime.now(timezone.utc)
    return certificado.not_valid_before_utc <= ahora <= certificado.not_valid_after_utc
