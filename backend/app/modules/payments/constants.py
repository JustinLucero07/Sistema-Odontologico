"""Vocabulary of the finance module.

Money in this module is `Decimal`, never `float`. A clinic reconciles a till at
the end of the day against physical cash, and a balance that is off by a cent
because 0.1 + 0.2 != 0.3 is a balance nobody trusts again.
"""

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

# Only cash physically enters the till, so only cash is counted at closing.
CASH_METHOD = "efectivo"

# Every amount is quantized to this before it is stored or compared.
CENTS = Decimal("0.01")

# A charge and a payment are both capped well below the column's precision so
# a typo of an extra digit is rejected rather than stored.
MAX_AMOUNT = Decimal("9999999.99")


def money(value: Decimal | float | int | str) -> Decimal:
    """Normalises anything money-shaped to two decimal places.

    Values arriving from Pydantic or from the legacy float-typed budget
    columns pass through here before they take part in any arithmetic, so a
    binary-float artefact can never reach a stored total."""
    return Decimal(str(value)).quantize(CENTS)
