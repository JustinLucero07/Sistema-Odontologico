from decimal import Decimal

STOCK_UNITS: list[tuple[str, str]] = [
    ("unidad", "Unidad"),
    ("caja", "Caja"),
    ("paquete", "Paquete"),
    ("frasco", "Frasco"),
    ("jeringa", "Jeringa"),
    ("ml", "Mililitro"),
    ("g", "Gramo"),
    ("par", "Par"),
]
STOCK_UNIT_CODES = {code for code, _ in STOCK_UNITS}

MOVEMENT_REASONS: list[tuple[str, str, int]] = [
    ("compra", "Compra / entrada", +1),
    ("devolucion_proveedor", "Devolución al proveedor", -1),
    ("consumo", "Consumo en tratamiento", -1),
    ("merma", "Merma o rotura", -1),
    ("vencimiento", "Retiro por vencimiento", -1),
    ("ajuste_positivo", "Ajuste de inventario (+)", +1),
    ("ajuste_negativo", "Ajuste de inventario (−)", -1),
]
MOVEMENT_SIGN = {code: sign for code, _, sign in MOVEMENT_REASONS}
MOVEMENT_REASON_CODES = set(MOVEMENT_SIGN)

QUANTITY_STEP = Decimal("0.001")
MAX_QUANTITY = Decimal("999999.999")


def quantity(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(QUANTITY_STEP)
