BUDGET_STATUSES: list[tuple[str, str]] = [
    ("borrador", "Borrador"),
    ("enviado", "Enviado"),
    ("visto", "Visto"),
    ("aceptado", "Aceptado"),
    ("rechazado", "Rechazado"),
]
BUDGET_STATUS_CODES = {code for code, _ in BUDGET_STATUSES}
