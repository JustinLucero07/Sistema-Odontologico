"""Catálogos del módulo de ortodoncia. Son códigos estables: la interfaz
muestra la etiqueta y la base guarda el código."""

CASE_STATUSES: list[tuple[str, str]] = [
    ("activo", "Activo"),
    ("retencion", "En retención"),
    ("pausa", "En pausa"),
    ("finalizado", "Finalizado"),
    ("abandono", "Abandonó"),
]
CASE_STATUS_CODES = {c for c, _ in CASE_STATUSES}

# ¿El paciente tiene microtornillos (TADs) colocados ahora mismo?
TAD_OPTIONS: list[tuple[str, str]] = [
    ("por_confirmar", "Por confirmar"),
    ("si", "Sí"),
    ("no", "No"),
]
TAD_CODES = {c for c, _ in TAD_OPTIONS}

# Estado de cada documento de la lista de control.
DOC_STATUSES: list[tuple[str, str]] = [
    ("por_revisar", "Por revisar"),
    ("pendiente", "Pendiente"),
    ("listo", "Listo"),
    ("no_requiere", "No requiere"),
]
DOC_STATUS_CODES = {c for c, _ in DOC_STATUSES}
DOC_FIELDS: list[tuple[str, str]] = [
    ("doc_xrays", "Radiografías"),
    ("doc_photos", "Fotografías"),
    ("doc_models", "Modelos"),
    ("doc_folder", "Carpeta clínica"),
]

APPLIANCES: list[str] = [
    "Brackets metálicos",
    "Brackets estéticos",
    "Brackets autoligado",
    "Alineadores",
    "Ortopedia funcional",
    "Aparatología removible",
    "Retenedores",
]

# Sugerencias para «Etapa del tratamiento» (texto libre: cada ortodoncista
# nombra sus fases a su manera).
STAGES: list[str] = [
    "Diagnóstico y registros",
    "Alineación y nivelación",
    "Cierre de espacios",
    "Corrección de clase / mordida",
    "Detallado y finalización",
    "Retención",
]

MAX_CONTROLS = 120
