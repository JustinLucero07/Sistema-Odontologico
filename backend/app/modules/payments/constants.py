from decimal import Decimal

PAYMENT_METHODS: list[tuple[str, str, bool]] = [
    # (code, label, needs a reference number)
    ("efectivo", "Efectivo", False),
    ("tarjeta_debito", "Tarjeta de débito", True),
    ("tarjeta_credito", "Tarjeta de crédito", True),
    ("transferencia", "Transferencia bancaria", True),
    ("deposito", "Depósito bancario", True),
    ("cheque", "Cheque", True),
    ("seguro", "Seguro / aseguradora", True),
    ("otro", "Otro medio", False),
]
PAYMENT_METHOD_CODES = {code for code, _, _ in PAYMENT_METHODS}
METHODS_REQUIRING_REFERENCE = {code for code, _, needs in PAYMENT_METHODS if needs}

CASH_METHOD = "efectivo"

# Every amount is quantized to this before it is stored or compared.
CENTS = Decimal("0.01")

MAX_AMOUNT = Decimal("9999999.99")


def money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENTS)
