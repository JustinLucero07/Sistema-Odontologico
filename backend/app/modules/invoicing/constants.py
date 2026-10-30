"""Catálogos de la ficha técnica de comprobantes electrónicos del SRI
(esquema offline). Son códigos del SRI, no nuestros: si el SRI publica una
ficha nueva, se revisan aquí y en ningún otro sitio."""

from decimal import Decimal

# Tipo de comprobante (codDoc).
FACTURA = "01"
NOTA_CREDITO = "04"

# Versiones del XML que se emiten.
VERSION_FACTURA = "1.1.0"
VERSION_NOTA_CREDITO = "1.1.0"

# Ambiente: 1 pruebas (celcer), 2 producción (cel).
PRUEBAS = "1"
PRODUCCION = "2"
AMBIENTES = {PRUEBAS: "Pruebas", PRODUCCION: "Producción"}

# Tipo de emisión: en el esquema offline solo existe la normal.
EMISION_NORMAL = "1"

# Impuesto: 2 = IVA.
IMPUESTO_IVA = "2"

# IVA por código de porcentaje: (etiqueta, tarifa). Los servicios de salud
# humana van con 0 %; lo estético, con la tarifa general.
IVA: dict[str, tuple[str, Decimal]] = {
    "0": ("IVA 0 %", Decimal("0")),
    "4": ("IVA 15 %", Decimal("15")),
    "5": ("IVA 5 %", Decimal("5")),
    "6": ("No objeto de IVA", Decimal("0")),
    "7": ("Exento de IVA", Decimal("0")),
}
IVA_POR_DEFECTO = "0"

# Tipo de identificación del comprador.
ID_RUC = "04"
ID_CEDULA = "05"
ID_PASAPORTE = "06"
ID_CONSUMIDOR_FINAL = "07"
ID_EXTERIOR = "08"
TIPOS_IDENTIFICACION = {
    ID_CEDULA: "Cédula",
    ID_RUC: "RUC",
    ID_PASAPORTE: "Pasaporte",
    ID_EXTERIOR: "Identificación del exterior",
    ID_CONSUMIDOR_FINAL: "Consumidor final",
}
CONSUMIDOR_FINAL_ID = "9999999999999"
CONSUMIDOR_FINAL_NOMBRE = "CONSUMIDOR FINAL"
# Una factura a consumidor final no puede pasar de este monto: por encima, el
# SRI exige identificar al comprador.
CONSUMIDOR_FINAL_MAXIMO = Decimal("50.00")

# Formas de pago del SRI.
FORMAS_PAGO = {
    "01": "Sin utilización del sistema financiero (efectivo)",
    "16": "Tarjeta de débito",
    "19": "Tarjeta de crédito",
    "20": "Otros con utilización del sistema financiero (transferencia, depósito, cheque)",
    "15": "Compensación de deudas",
    "17": "Dinero electrónico",
    "18": "Tarjeta prepago",
}
# Del medio de pago de la caja a la forma de pago del SRI.
FORMA_PAGO_DE_METODO = {
    "efectivo": "01",
    "tarjeta_debito": "16",
    "tarjeta_credito": "19",
    "transferencia": "20",
    "deposito": "20",
    "cheque": "20",
    "seguro": "20",
    "otro": "01",
}

# Leyendas del régimen tributario (infoTributaria/contribuyenteRimpe).
LEYENDA_RIMPE = {
    "rimpe_emprendedor": "CONTRIBUYENTE RÉGIMEN RIMPE",
    "rimpe_negocio_popular": "CONTRIBUYENTE NEGOCIO POPULAR - RÉGIMEN RIMPE",
}

# Estados de un comprobante en el sistema.
PENDIENTE = "pendiente"          # creado; aún no lo recibe el SRI
RECIBIDA = "recibida"            # el SRI lo recibió; falta la autorización
AUTORIZADA = "autorizada"
DEVUELTA = "devuelta"            # el SRI lo rechazó al recibirlo
NO_AUTORIZADA = "no_autorizada"  # el SRI lo recibió pero no lo autorizó
DESCARTADA = "descartada"        # rechazada y dada de baja: no vale como factura
ESTADOS = {
    PENDIENTE: "Pendiente de envío",
    RECIBIDA: "En autorización",
    AUTORIZADA: "Autorizada",
    DEVUELTA: "Devuelta por el SRI",
    NO_AUTORIZADA: "No autorizada",
    DESCARTADA: "Descartada",
}
# Los que siguen su curso solos (el proceso en segundo plano los retoma).
EN_CURSO = {PENDIENTE, RECIBIDA}
# Los que ocupan un cargo: un cargo no se puede facturar dos veces.
VIGENTES = {PENDIENTE, RECIBIDA, AUTORIZADA}

# Servicios web del SRI (esquema offline).
SRI_URLS = {
    PRUEBAS: "https://celcer.sri.gob.ec/comprobantes-electronicos-ws",
    PRODUCCION: "https://cel.sri.gob.ec/comprobantes-electronicos-ws",
}

# Reintentos ante fallas de conexión: minutos de espera según el intento.
ESPERAS_REINTENTO = [1, 2, 5, 10, 30, 60]
