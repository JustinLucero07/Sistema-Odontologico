"""XML de factura y nota de crédito según la ficha técnica del SRI."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from lxml import etree

from app.modules.invoicing.constants import (
    FACTURA,
    IMPUESTO_IVA,
    IVA,
    LEYENDA_RIMPE,
    NOTA_CREDITO,
    VERSION_FACTURA,
    VERSION_NOTA_CREDITO,
)

CENTAVOS = Decimal("0.01")


def d2(valor: Decimal) -> str:
    return str(Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP))


def d6(valor: Decimal) -> str:
    """Cantidad y precio unitario: hasta 6 decimales, sin ceros de sobra."""
    texto = f"{Decimal(valor).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP):f}"
    entero, _, dec = texto.partition(".")
    dec = dec.rstrip("0")
    return f"{entero}.{dec.ljust(2, '0')}"


def limpio(texto: str | None, maximo: int = 300) -> str:
    """El SRI rechaza saltos de línea y espacios dobles en los textos."""
    return " ".join((texto or "").split())[:maximo]


@dataclass
class Emisor:
    ruc: str
    razon_social: str
    nombre_comercial: str | None
    direccion_matriz: str
    direccion_establecimiento: str
    obligado_contabilidad: bool
    contribuyente_especial: str | None
    regimen: str
    agente_retencion: str | None


@dataclass
class Linea:
    codigo: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    subtotal: Decimal
    codigo_iva: str
    tarifa: Decimal
    iva: Decimal


@dataclass
class Comprobante:
    tipo: str
    ambiente: str
    clave_acceso: str
    establecimiento: str
    punto_emision: str
    secuencial: int
    fecha_emision: str  # dd/mm/aaaa
    tipo_id_comprador: str
    id_comprador: str
    razon_social_comprador: str
    direccion_comprador: str | None
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    lineas: list[Linea]
    forma_pago: str = "01"
    info_adicional: dict[str, str] = field(default_factory=dict)
    # Nota de crédito: la factura que modifica.
    doc_modificado_numero: str | None = None
    doc_modificado_fecha: str | None = None
    motivo: str | None = None


def _sub(padre, nombre, texto=None):
    el = etree.SubElement(padre, nombre)
    if texto is not None:
        el.text = str(texto)
    return el


def _totales_por_iva(lineas: list[Linea]) -> dict[str, tuple[Decimal, Decimal, Decimal]]:
    """(base, tarifa, valor) por código de IVA."""
    grupos: dict[str, tuple[Decimal, Decimal, Decimal]] = {}
    for ln in lineas:
        base, tarifa, valor = grupos.get(ln.codigo_iva, (Decimal(0), ln.tarifa, Decimal(0)))
        grupos[ln.codigo_iva] = (base + ln.subtotal, tarifa, valor + ln.iva)
    return grupos


def construir(emisor: Emisor, c: Comprobante) -> etree._Element:
    es_factura = c.tipo == FACTURA
    raiz = etree.Element(
        "factura" if es_factura else "notaCredito",
        id="comprobante",
        version=VERSION_FACTURA if es_factura else VERSION_NOTA_CREDITO,
    )

    it = _sub(raiz, "infoTributaria")
    _sub(it, "ambiente", c.ambiente)
    _sub(it, "tipoEmision", "1")
    _sub(it, "razonSocial", limpio(emisor.razon_social))
    if emisor.nombre_comercial:
        _sub(it, "nombreComercial", limpio(emisor.nombre_comercial))
    _sub(it, "ruc", emisor.ruc)
    _sub(it, "claveAcceso", c.clave_acceso)
    _sub(it, "codDoc", c.tipo)
    _sub(it, "estab", c.establecimiento)
    _sub(it, "ptoEmi", c.punto_emision)
    _sub(it, "secuencial", f"{c.secuencial:09d}")
    _sub(it, "dirMatriz", limpio(emisor.direccion_matriz))
    if emisor.agente_retencion:
        _sub(it, "agenteRetencion", emisor.agente_retencion)
    if emisor.regimen in LEYENDA_RIMPE:
        _sub(it, "contribuyenteRimpe", LEYENDA_RIMPE[emisor.regimen])

    info = _sub(raiz, "infoFactura" if es_factura else "infoNotaCredito")
    _sub(info, "fechaEmision", c.fecha_emision)
    _sub(info, "dirEstablecimiento", limpio(emisor.direccion_establecimiento))
    if es_factura:
        # El orden de los elementos lo fija el XSD del SRI y difiere entre
        # factura y nota de crédito.
        if emisor.contribuyente_especial:
            _sub(info, "contribuyenteEspecial", emisor.contribuyente_especial)
        _sub(info, "obligadoContabilidad", "SI" if emisor.obligado_contabilidad else "NO")
        _sub(info, "tipoIdentificacionComprador", c.tipo_id_comprador)
        _sub(info, "razonSocialComprador", limpio(c.razon_social_comprador))
        _sub(info, "identificacionComprador", c.id_comprador)
        if c.direccion_comprador:
            _sub(info, "direccionComprador", limpio(c.direccion_comprador))
        _sub(info, "totalSinImpuestos", d2(c.subtotal))
        _sub(info, "totalDescuento", d2(c.descuento))
    else:
        _sub(info, "tipoIdentificacionComprador", c.tipo_id_comprador)
        _sub(info, "razonSocialComprador", limpio(c.razon_social_comprador))
        _sub(info, "identificacionComprador", c.id_comprador)
        if emisor.contribuyente_especial:
            _sub(info, "contribuyenteEspecial", emisor.contribuyente_especial)
        _sub(info, "obligadoContabilidad", "SI" if emisor.obligado_contabilidad else "NO")
        _sub(info, "codDocModificado", FACTURA)
        _sub(info, "numDocModificado", c.doc_modificado_numero)
        _sub(info, "fechaEmisionDocSustento", c.doc_modificado_fecha)
        _sub(info, "totalSinImpuestos", d2(c.subtotal))
        _sub(info, "valorModificacion", d2(c.total))
        _sub(info, "moneda", "DOLAR")

    impuestos = _sub(info, "totalConImpuestos")
    for codigo, (base, tarifa, valor) in _totales_por_iva(c.lineas).items():
        ti = _sub(impuestos, "totalImpuesto")
        _sub(ti, "codigo", IMPUESTO_IVA)
        _sub(ti, "codigoPorcentaje", codigo)
        if es_factura:
            _sub(ti, "descuentoAdicional", "0.00")
        _sub(ti, "baseImponible", d2(base))
        if es_factura:
            _sub(ti, "tarifa", d2(tarifa))
        _sub(ti, "valor", d2(valor))

    if es_factura:
        _sub(info, "propina", "0.00")
        _sub(info, "importeTotal", d2(c.total))
        _sub(info, "moneda", "DOLAR")
        pagos = _sub(info, "pagos")
        pago = _sub(pagos, "pago")
        _sub(pago, "formaPago", c.forma_pago)
        _sub(pago, "total", d2(c.total))
    else:
        _sub(info, "motivo", limpio(c.motivo))

    detalles = _sub(raiz, "detalles")
    for ln in c.lineas:
        det = _sub(detalles, "detalle")
        _sub(det, "codigoPrincipal" if es_factura else "codigoInterno", limpio(ln.codigo, 25))
        _sub(det, "descripcion", limpio(ln.descripcion))
        _sub(det, "cantidad", d6(ln.cantidad))
        _sub(det, "precioUnitario", d6(ln.precio_unitario))
        _sub(det, "descuento", d2(ln.descuento))
        _sub(det, "precioTotalSinImpuesto", d2(ln.subtotal))
        imp = _sub(_sub(det, "impuestos"), "impuesto")
        _sub(imp, "codigo", IMPUESTO_IVA)
        _sub(imp, "codigoPorcentaje", ln.codigo_iva)
        _sub(imp, "tarifa", d2(ln.tarifa))
        _sub(imp, "baseImponible", d2(ln.subtotal))
        _sub(imp, "valor", d2(ln.iva))

    adicional = {k: limpio(v) for k, v in c.info_adicional.items() if v and limpio(v)}
    if adicional:
        ia = _sub(raiz, "infoAdicional")
        for nombre, valor in list(adicional.items())[:15]:
            campo = _sub(ia, "campoAdicional", valor)
            campo.set("nombre", nombre)
    return raiz


def tarifa_de(codigo: str) -> Decimal:
    return IVA.get(codigo, IVA["0"])[1]


__all__ = ["Comprobante", "Emisor", "Linea", "construir", "d2", "tarifa_de", "NOTA_CREDITO"]
