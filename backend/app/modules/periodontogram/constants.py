PERIODONTAL_SITES: list[tuple[str, str]] = [
    ("vestibular_distal", "Vestibular distal"),
    ("vestibular_central", "Vestibular central"),
    ("vestibular_mesial", "Vestibular mesial"),
    ("lingual_distal", "Lingual/palatino distal"),
    ("lingual_central", "Lingual/palatino central"),
    ("lingual_mesial", "Lingual/palatino mesial"),
]
PERIODONTAL_SITE_CODES = {code for code, _ in PERIODONTAL_SITES}

MAX_PROBING_DEPTH_MM = 15
MIN_RECESSION_MM = -10
MAX_RECESSION_MM = 20

MAX_MOBILITY = 3
MAX_FURCATION = 3
