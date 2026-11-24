TOOTH_CONDITIONS: list[tuple[str, str]] = [
    ("sano", "Sano"),
    ("caries", "Caries"),
    ("restauracion", "Restauración"),
    ("restauracion_defectuosa", "Restauración defectuosa"),
    ("corona", "Corona"),
    ("puente", "Puente"),
    ("implante", "Implante"),
    ("ausente", "Ausente"),
    ("extraccion_indicada", "Extracción indicada"),
    ("extraccion_realizada", "Extracción realizada"),
    ("endodoncia", "Endodoncia"),
    ("fractura", "Fractura"),
    ("sellante", "Sellante"),
    ("protesis", "Prótesis"),
    ("movilidad", "Movilidad"),
    ("diente_retenido", "Diente retenido"),
    ("tratamiento_pendiente", "Tratamiento pendiente"),
    ("tratamiento_realizado", "Tratamiento realizado"),
]
TOOTH_CONDITION_CODES = {code for code, _ in TOOTH_CONDITIONS}

TOOTH_SURFACES: list[tuple[str, str]] = [
    ("whole", "Diente completo"),
    ("mesial", "Mesial"),
    ("distal", "Distal"),
    ("vestibular", "Vestibular"),
    ("lingual", "Lingual/Palatina"),
    ("oclusal", "Oclusal/Incisal"),
]
TOOTH_SURFACE_CODES = {code for code, _ in TOOTH_SURFACES}

PERMANENT_FDI_NUMBERS = [f"{quadrant}{tooth}" for quadrant in (1, 2, 3, 4) for tooth in range(1, 9)]
TEMPORARY_FDI_NUMBERS = [f"{quadrant}{tooth}" for quadrant in (5, 6, 7, 8) for tooth in range(1, 6)]
VALID_FDI_NUMBERS = set(PERMANENT_FDI_NUMBERS) | set(TEMPORARY_FDI_NUMBERS)
