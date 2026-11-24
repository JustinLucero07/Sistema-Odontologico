FREQUENCIES: list[tuple[str, str, int]] = [
    # (código, etiqueta, días entre cuotas)
    ("semanal", "Semanal", 7),
    ("quincenal", "Quincenal", 15),
    ("mensual", "Mensual", 30),
]
FREQUENCY_DAYS = {code: days for code, _, days in FREQUENCIES}
FREQUENCY_LABELS = {code: label for code, label, _ in FREQUENCIES}

MAX_MONTHLY_RATE = 5

MAX_INSTALLMENTS = 48
