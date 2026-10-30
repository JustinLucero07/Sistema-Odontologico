"""Firma XAdES-BES envuelta (enveloped), la que exige el SRI.

Estructura: tres referencias en SignedInfo —las propiedades firmadas, el
certificado (KeyInfo) y el comprobante (#comprobante, con la transformación
enveloped)—, RSA-SHA1 y SHA1 como pide la ficha técnica.

Los espacios de nombres se declaran a propósito así: `ds` en la firma y
`etsi` recién en QualifyingProperties. Cada parte que se resume (SignedInfo,
KeyInfo, SignedProperties) usa TODOS los espacios que tiene en alcance, así
que la canonicalización inclusiva da el mismo resultado se calcule como se
calcule; es la causa más común del rechazo «firma inválida»."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509 import Certificate
from lxml import etree

DS = "http://www.w3.org/2000/09/xmldsig#"
ETSI = "http://uri.etsi.org/01903/v1.3.2#"
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
RSA_SHA1 = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
SHA1 = "http://www.w3.org/2000/09/xmldsig#sha1"
ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
ECUADOR = timezone(timedelta(hours=-5))


def _ds(nombre: str) -> str:
    return f"{{{DS}}}{nombre}"


def _etsi(nombre: str) -> str:
    return f"{{{ETSI}}}{nombre}"


def _c14n(elemento: etree._Element) -> bytes:
    return etree.tostring(elemento, method="c14n", exclusive=False, with_comments=False)


def _sha1_b64(datos: bytes) -> str:
    return base64.b64encode(hashlib.sha1(datos).digest()).decode()


def _b64_entero(n: int) -> str:
    return base64.b64encode(n.to_bytes((n.bit_length() + 7) // 8, "big")).decode()


def _sub(padre, etiqueta, texto=None, **atributos):
    el = etree.SubElement(padre, etiqueta, **atributos)
    if texto is not None:
        el.text = texto
    return el


def firmar(raiz: etree._Element, llave: RSAPrivateKey, certificado: Certificate, ahora: datetime | None = None) -> bytes:
    """Firma el comprobante (que debe tener id="comprobante") y devuelve el
    XML completo listo para enviar."""
    n = secrets.randbelow(900000) + 100000
    id_firma = f"Signature{n}"
    id_info = f"Signature-SignedInfo{n}"
    id_props = f"{id_firma}-SignedProperties{n}"
    id_ref_props = f"SignedPropertiesID{n}"
    id_cert = f"Certificate{n}"
    id_ref_doc = f"Reference-ID-{n}"
    id_valor = f"SignatureValue{n}"
    id_objeto = f"{id_firma}-Object{n}"

    # 1. Resumen del comprobante, antes de que contenga la firma (es lo mismo
    #    que aplicar la transformación enveloped).
    resumen_doc = _sha1_b64(_c14n(raiz))
    der = certificado.public_bytes(serialization.Encoding.DER)

    firma = etree.SubElement(raiz, _ds("Signature"), nsmap={"ds": DS}, Id=id_firma)
    info = _sub(firma, _ds("SignedInfo"), Id=id_info)
    _sub(info, _ds("CanonicalizationMethod"), Algorithm=C14N)
    _sub(info, _ds("SignatureMethod"), Algorithm=RSA_SHA1)

    ref_props = _sub(info, _ds("Reference"), Id=id_ref_props, Type="http://uri.etsi.org/01903#SignedProperties", URI=f"#{id_props}")
    _sub(ref_props, _ds("DigestMethod"), Algorithm=SHA1)
    valor_props = _sub(ref_props, _ds("DigestValue"))

    ref_cert = _sub(info, _ds("Reference"), URI=f"#{id_cert}")
    _sub(ref_cert, _ds("DigestMethod"), Algorithm=SHA1)
    valor_cert = _sub(ref_cert, _ds("DigestValue"))

    ref_doc = _sub(info, _ds("Reference"), Id=id_ref_doc, URI="#comprobante")
    _sub(_sub(ref_doc, _ds("Transforms")), _ds("Transform"), Algorithm=ENVELOPED)
    _sub(ref_doc, _ds("DigestMethod"), Algorithm=SHA1)
    _sub(ref_doc, _ds("DigestValue"), resumen_doc)

    valor_firma = _sub(firma, _ds("SignatureValue"), Id=id_valor)

    key_info = _sub(firma, _ds("KeyInfo"), Id=id_cert)
    _sub(_sub(key_info, _ds("X509Data")), _ds("X509Certificate"), base64.b64encode(der).decode())
    publica = certificado.public_key().public_numbers()
    rsa = _sub(_sub(key_info, _ds("KeyValue")), _ds("RSAKeyValue"))
    _sub(rsa, _ds("Modulus"), _b64_entero(publica.n))
    _sub(rsa, _ds("Exponent"), _b64_entero(publica.e))

    objeto = _sub(firma, _ds("Object"), Id=id_objeto)
    calificadas = etree.SubElement(objeto, _etsi("QualifyingProperties"), nsmap={"etsi": ETSI}, Target=f"#{id_firma}")
    props = _sub(calificadas, _etsi("SignedProperties"), Id=id_props)
    firmadas = _sub(props, _etsi("SignedSignatureProperties"))
    momento = (ahora or datetime.now(ECUADOR)).astimezone(ECUADOR).replace(microsecond=0)
    _sub(firmadas, _etsi("SigningTime"), momento.isoformat())
    cert = _sub(_sub(firmadas, _etsi("SigningCertificate")), _etsi("Cert"))
    resumen_certificado = _sub(cert, _etsi("CertDigest"))
    _sub(resumen_certificado, _ds("DigestMethod"), Algorithm=SHA1)
    _sub(resumen_certificado, _ds("DigestValue"), _sha1_b64(der))
    emisor = _sub(cert, _etsi("IssuerSerial"))
    _sub(emisor, _ds("X509IssuerName"), certificado.issuer.rfc4514_string())
    _sub(emisor, _ds("X509SerialNumber"), str(certificado.serial_number))
    formato = _sub(_sub(props, _etsi("SignedDataObjectProperties")), _etsi("DataObjectFormat"), ObjectReference=f"#{id_ref_doc}")
    _sub(formato, _etsi("Description"), "contenido comprobante")
    _sub(formato, _etsi("MimeType"), "text/xml")

    # 2. Resúmenes de las partes que ya están en su lugar dentro del documento.
    valor_props.text = _sha1_b64(_c14n(props))
    valor_cert.text = _sha1_b64(_c14n(key_info))

    # 3. La firma propiamente dicha, sobre SignedInfo canonicalizado.
    firma_bytes = llave.sign(_c14n(info), padding.PKCS1v15(), hashes.SHA1())
    valor_firma.text = base64.b64encode(firma_bytes).decode()

    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")
