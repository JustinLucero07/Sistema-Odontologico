PRIVACY_POLICY_VERSION = "2026-09"
CONFIDENTIALITY_VERSION = "2026-09"
TERMS_VERSION = "2026-10"

# Solicitudes de los titulares (derechos LOPDP) y su plazo de respuesta.
RIGHTS_KINDS: dict[str, str] = {
    "acceso": "Acceso",
    "rectificacion": "Rectificación y actualización",
    "eliminacion": "Eliminación",
    "oposicion": "Oposición",
    "portabilidad": "Portabilidad",
    "suspension": "Suspensión del tratamiento",
}
RIGHTS_STATUSES: dict[str, str] = {
    "pendiente": "Pendiente",
    "en_proceso": "En proceso",
    "respondida": "Respondida",
    "rechazada": "Rechazada con motivo",
}
RIGHTS_RESPONSE_DAYS = 15

TAX_REGIMES: dict[str, str] = {
    "general": "Régimen general",
    "rimpe_emprendedor": "RIMPE Emprendedor",
    "rimpe_negocio_popular": "RIMPE Negocio popular",
}

# Qué se registra de cada paciente.
CONSENT_KINDS: dict[str, str] = {
    "aviso_privacidad": "Aviso de privacidad entregado",
    "comunicaciones": "Recordatorios y mensajes por WhatsApp o correo",
}

CONSENT_METHODS: dict[str, str] = {
    "firma_presencial": "Firmado en la clínica",
    "verbal": "De palabra, en presencia del personal",
    "digital": "Por medio digital",
}

ACCESS_DEDUP_MINUTES = 15

EXPORT_EXCLUDED_COLUMNS = {"clinic_id", "token_hash", "hashed_password"}
