BUDGET_STATUSES: list[tuple[str, str]] = [
    ("borrador", "Borrador"),
    ("enviado", "Enviado"),
    ("visto", "Visto"),
    ("aceptado", "Aceptado"),
    ("rechazado", "Rechazado"),
    ("anulado", "Anulado"),
]
# Estados en los que el presupuesto todavía se puede corregir.
EDITABLE_STATUSES = {"borrador", "enviado", "visto"}
BUDGET_STATUS_CODES = {code for code, _ in BUDGET_STATUSES}
