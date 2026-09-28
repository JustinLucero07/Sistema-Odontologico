"""Categorías de gasto de una clínica dental.

Son las que un contador espera ver separadas en un estado de resultados: los
insumos y el laboratorio son costo directo del tratamiento; el resto, gasto de
operación."""

EXPENSE_CATEGORIES: list[tuple[str, str]] = [
    ("insumos", "Insumos y materiales dentales"),
    ("laboratorio", "Laboratorio dental"),
    ("sueldos", "Sueldos y honorarios"),
    ("arriendo", "Arriendo del local"),
    ("servicios_basicos", "Luz, agua, internet y teléfono"),
    ("equipos", "Equipos e instrumental"),
    ("mantenimiento", "Mantenimiento y reparaciones"),
    ("limpieza", "Limpieza y desechos"),
    ("marketing", "Publicidad y marketing"),
    ("impuestos", "Impuestos, permisos y tasas"),
    ("software", "Software y suscripciones"),
    ("otros", "Otros gastos"),
]
EXPENSE_CATEGORY_CODES = {code for code, _ in EXPENSE_CATEGORIES}
