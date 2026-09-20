"""Vocabulary of the periodontal chart.

A periodontal exam is recorded at SIX sites per tooth — three on the buccal
wall and three on the lingual/palatal wall — because a pocket can be deep at
one corner of a tooth and healthy at the next. Recording one number per tooth
is the classic way to miss localised periodontitis, so the schema does not
allow it.
"""

PERIODONTAL_SITES: list[tuple[str, str]] = [
    ("vestibular_distal", "Vestibular distal"),
    ("vestibular_central", "Vestibular central"),
    ("vestibular_mesial", "Vestibular mesial"),
    ("lingual_distal", "Lingual/palatino distal"),
    ("lingual_central", "Lingual/palatino central"),
    ("lingual_mesial", "Lingual/palatino mesial"),
]
PERIODONTAL_SITE_CODES = {code for code, _ in PERIODONTAL_SITES}

# Millimetres. A probe is 15 mm; anything beyond that is a typo, not a finding.
MAX_PROBING_DEPTH_MM = 15
# Recession can be negative when the margin sits coronal to the CEJ (an
# overgrown or swollen gingiva), which is why the floor is below zero.
MIN_RECESSION_MM = -10
MAX_RECESSION_MM = 20

# Miller mobility 0–3 and Hamp furcation 0–3 are the scales in routine use.
MAX_MOBILITY = 3
MAX_FURCATION = 3
