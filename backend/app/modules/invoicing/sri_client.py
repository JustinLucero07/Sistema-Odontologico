"""Servicios web del SRI (esquema offline): recepción y autorización.

Son SOAP; se arma el sobre a mano porque son dos operaciones fijas y así no
hace falta descargar el WSDL en cada arranque."""

import base64
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import httpx
from lxml import etree

from app.modules.invoicing.constants import FACTURA, SRI_URLS

TIEMPO = httpx.Timeout(20.0, connect=8.0)
XSD = Path(__file__).parent / "xsd"


class SriNoDisponible(Exception):
    """No hubo respuesta (red, SRI caído): se reintenta más tarde."""


@dataclass
class Mensaje:
    identificador: str
    mensaje: str
    informacion: str = ""
    tipo: str = ""

    def como_dict(self) -> dict:
        return {"identificador": self.identificador, "mensaje": self.mensaje, "informacion": self.informacion, "tipo": self.tipo}


@dataclass
class Recepcion:
    estado: str  # RECIBIDA | DEVUELTA
    mensajes: list[Mensaje] = field(default_factory=list)

    @property
    def ya_registrada(self) -> bool:
        """El SRI ya tiene esta clave (un envío anterior llegó aunque no
        recibimos la respuesta): se pasa directo a consultar la autorización."""
        return any(m.identificador == "43" or "REGISTRADA" in m.mensaje.upper() for m in self.mensajes)


@dataclass
class Autorizacion:
    estado: str  # AUTORIZADO | NO AUTORIZADO | EN PROCESO | SIN_RESPUESTA
    numero: str | None = None
    fecha: datetime | None = None
    comprobante: str | None = None
    mensajes: list[Mensaje] = field(default_factory=list)


@lru_cache
def _esquema(tipo: str) -> etree.XMLSchema:
    nombre = "factura_V1.1.0.xsd" if tipo == FACTURA else "notaCredito_V1.1.0.xsd"
    return etree.XMLSchema(etree.parse(str(XSD / nombre)))


def errores_de_esquema(xml: bytes, tipo: str) -> list[str]:
    """Valida contra el XSD oficial antes de enviar: un error se ve aquí, en
    español y al instante, en vez de como rechazo del SRI."""
    esquema = _esquema(tipo)
    if esquema.validate(etree.fromstring(xml)):
        return []
    return [f"{e.path}: {e.message}" for e in esquema.error_log][:5]


def _sobre(espacio: str, operacion: str, cuerpo: str) -> bytes:
    return (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:ec="{espacio}"><soapenv:Header/><soapenv:Body>'
        f"<ec:{operacion}>{cuerpo}</ec:{operacion}>"
        "</soapenv:Body></soapenv:Envelope>"
    ).encode()


async def _llamar(url: str, sobre: bytes) -> etree._Element:
    try:
        async with httpx.AsyncClient(timeout=TIEMPO) as cliente:
            r = await cliente.post(url, content=sobre, headers={"Content-Type": "text/xml; charset=utf-8"})
    except httpx.HTTPError as e:
        raise SriNoDisponible(f"Sin conexión con el SRI ({type(e).__name__}).") from e
    if r.status_code >= 500 and b"Envelope" not in r.content:
        raise SriNoDisponible(f"El SRI respondió con error {r.status_code}.")
    try:
        return etree.fromstring(r.content)
    except etree.XMLSyntaxError as e:
        raise SriNoDisponible("El SRI devolvió una respuesta ilegible.") from e


def _texto(el: etree._Element | None, ruta: str) -> str:
    if el is None:
        return ""
    hallado = el.find(ruta)
    return (hallado.text or "").strip() if hallado is not None else ""


def _mensajes(el: etree._Element | None) -> list[Mensaje]:
    if el is None:
        return []
    return [
        Mensaje(_texto(m, "identificador"), _texto(m, "mensaje"), _texto(m, "informacionAdicional"), _texto(m, "tipo"))
        for m in el.iter("mensaje")
        if m.find("identificador") is not None
    ]


async def enviar(xml_firmado: bytes, ambiente: str) -> Recepcion:
    url = f"{SRI_URLS[ambiente]}/RecepcionComprobantesOffline"
    cuerpo = f"<xml>{base64.b64encode(xml_firmado).decode()}</xml>"
    raiz = await _llamar(url, _sobre("http://ec.gob.sri.ws.recepcion", "validarComprobante", cuerpo))
    respuesta = next(raiz.iter("RespuestaRecepcionComprobante"), None)
    if respuesta is None:
        raise SriNoDisponible("Respuesta de recepción sin contenido.")
    return Recepcion(estado=_texto(respuesta, "estado").upper(), mensajes=_mensajes(respuesta))


async def consultar(clave: str, ambiente: str) -> Autorizacion:
    url = f"{SRI_URLS[ambiente]}/AutorizacionComprobantesOffline"
    cuerpo = f"<claveAccesoComprobante>{clave}</claveAccesoComprobante>"
    raiz = await _llamar(url, _sobre("http://ec.gob.sri.ws.autorizacion", "autorizacionComprobante", cuerpo))
    autorizaciones = list(raiz.iter("autorizacion"))
    if not autorizaciones:
        return Autorizacion(estado="SIN_RESPUESTA")
    # Si hay varias (reenvíos), manda la autorizada; si no, la última.
    elegida = next((a for a in autorizaciones if _texto(a, "estado").upper() == "AUTORIZADO"), autorizaciones[-1])
    fecha = None
    texto_fecha = _texto(elegida, "fechaAutorizacion")
    if texto_fecha:
        try:
            fecha = datetime.fromisoformat(texto_fecha)
        except ValueError:
            fecha = None
    return Autorizacion(
        estado=_texto(elegida, "estado").upper(),
        numero=_texto(elegida, "numeroAutorizacion") or None,
        fecha=fecha,
        comprobante=_texto(elegida, "comprobante") or None,
        mensajes=_mensajes(elegida),
    )
