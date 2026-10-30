"""Ayudas para probar la facturación sin tocar el SRI real: una firma .p12 de
prueba (autofirmada) y un SRI simulado que responde lo que se le pida."""

import datetime as dt

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.modules.invoicing import sri_client

CLAVE_P12 = "clave-de-prueba"
RUC_PRUEBA = "1710034065001"


def p12_de_prueba(vence_en_dias: int = 365) -> tuple[bytes, x509.Certificate]:
    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CONSULTORIO DE PRUEBA"), x509.NameAttribute(NameOID.COUNTRY_NAME, "EC")])
    ahora = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder().subject_name(nombre).issuer_name(nombre).public_key(llave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - dt.timedelta(days=400))
        .not_valid_after(ahora + dt.timedelta(days=vence_en_dias))
        .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
        .sign(llave, hashes.SHA256())
    )
    datos = pkcs12.serialize_key_and_certificates(b"prueba", llave, cert, None, serialization.BestAvailableEncryption(CLAVE_P12.encode()))
    return datos, cert


class SriFalso:
    """Reemplaza enviar/consultar. `recepcion` y `autorizacion` deciden la
    respuesta; `caido` simula que el SRI no contesta."""

    def __init__(self, monkeypatch):
        self.recepcion = "RECIBIDA"
        self.autorizacion = "AUTORIZADO"
        self.caido = False
        self.mensajes: list[sri_client.Mensaje] = []
        self.enviados: list[bytes] = []
        monkeypatch.setattr(sri_client, "enviar", self._enviar)
        monkeypatch.setattr(sri_client, "consultar", self._consultar)

    async def _enviar(self, xml: bytes, ambiente: str):
        if self.caido:
            raise sri_client.SriNoDisponible("Sin conexión con el SRI (prueba).")
        self.enviados.append(xml)
        return sri_client.Recepcion(estado=self.recepcion, mensajes=list(self.mensajes))

    async def _consultar(self, clave: str, ambiente: str):
        if self.caido:
            raise sri_client.SriNoDisponible("Sin conexión con el SRI (prueba).")
        if self.autorizacion == "AUTORIZADO":
            return sri_client.Autorizacion(
                estado="AUTORIZADO", numero=clave, fecha=dt.datetime.now(dt.timezone.utc),
                comprobante=self.enviados[-1].decode() if self.enviados else None,
            )
        return sri_client.Autorizacion(estado=self.autorizacion, mensajes=list(self.mensajes))


async def preparar_emisor(client, h, p12: bytes | None = None) -> None:
    """Deja la consulta lista para facturar: RUC, razón social, dirección y firma."""
    r = await client.put("/api/v1/clinics/me", headers=h, json={
        "legal_name": "Consultorio Dental de Prueba", "tax_id": RUC_PRUEBA, "address": "Av. Amazonas N1 y Colón, Quito",
    })
    assert r.status_code == 200, r.text
    datos = p12 or p12_de_prueba()[0]
    r = await client.post(
        "/api/v1/invoicing/certificate", headers=h,
        files={"file": ("firma.p12", datos, "application/x-pkcs12")}, data={"password": CLAVE_P12},
    )
    assert r.status_code == 200, r.text
