"""Vocabulary of the inventory module.

Stock is held as a signed ledger of MOVEMENTS, never as a quantity column that
gets updated in place. A stored quantity is a second source of truth: the first
time two hands touch it at once, or a movement is corrected, the number and its
history disagree and neither can be trusted.
"""

from decimal import Decimal

# How a unit is counted. A box of gloves and a gram of composite are both
# "stock", but nobody orders 0.5 boxes, so the unit decides the step size.
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

# Why stock moved. The sign is fixed by the reason, not chosen by the caller:
# an "entrada" can never decrement and a "consumo" can never increment.
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
    """Three decimals: enough for grams and millilitres, and exact, so a
    running stock total never drifts the way a float one would."""
    return Decimal(str(value)).quantize(QUANTITY_STEP)
