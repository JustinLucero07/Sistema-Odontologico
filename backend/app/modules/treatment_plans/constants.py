TREATMENT_PLAN_ITEM_STATUSES: list[tuple[str, str]] = [
    ("propuesto", "Propuesto"),
    ("aprobado", "Aprobado"),
    ("en_progreso", "En progreso"),
    ("completado", "Completado"),
    ("cancelado", "Cancelado"),
    ("rechazado", "Rechazado"),
]
TREATMENT_PLAN_ITEM_STATUS_CODES = {code for code, _ in TREATMENT_PLAN_ITEM_STATUSES}

# Statuses that count as "done" when computing a plan's progress percentage.
COMPLETED_STATUSES = {"completado"}
# Statuses excluded from the progress denominator entirely (they were never going to happen).
VOID_STATUSES = {"cancelado", "rechazado"}
