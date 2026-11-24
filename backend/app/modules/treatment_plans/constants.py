TREATMENT_PLAN_ITEM_STATUSES: list[tuple[str, str]] = [
    ("propuesto", "Propuesto"),
    ("aprobado", "Aprobado"),
    ("en_progreso", "En progreso"),
    ("completado", "Completado"),
    ("cancelado", "Cancelado"),
    ("rechazado", "Rechazado"),
]
TREATMENT_PLAN_ITEM_STATUS_CODES = {code for code, _ in TREATMENT_PLAN_ITEM_STATUSES}

COMPLETED_STATUSES = {"completado"}
VOID_STATUSES = {"cancelado", "rechazado"}
