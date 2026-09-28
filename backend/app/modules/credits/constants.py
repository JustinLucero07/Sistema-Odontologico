FREQUENCIES: list[tuple[str, str, int]] = [
    # (código, etiqueta, días entre cuotas)
    ("semanal", "Semanal", 7),
    ("quincenal", "Quincenal", 15),
    ("mensual", "Mensual", 30),
]
FREQUENCY_DAYS = {code: days for code, _, days in FREQUENCIES}
FREQUENCY_LABELS = {code: label for code, label, _ in FREQUENCIES}

# Tope de seguridad para la tasa mensual que acepta el sistema. No es la tasa
# legal: la máxima la fija el Banco Central del Ecuador y cambia; la clínica
# debe respetarla. Esto solo evita un error de tipeo (p. ej. 30 en vez de 3).
MAX_MONTHLY_RATE = 5

MAX_INSTALLMENTS = 48
