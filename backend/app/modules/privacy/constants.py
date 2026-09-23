"""Versiones de los textos legales.

Cuando cambia el texto de la política o del acuerdo de confidencialidad se sube
la versión: los registros guardan con qué versión se informó o aceptó, y al
personal se le vuelve a pedir la aceptación del texto nuevo.
"""

PRIVACY_POLICY_VERSION = "2026-09"
CONFIDENTIALITY_VERSION = "2026-09"

# Qué se registra de cada paciente.
CONSENT_KINDS: dict[str, str] = {
    # Informar es obligatorio al recoger los datos (LOPDP, derecho a ser
    # informado). No es un "sí/no": se deja constancia de que se entregó.
    "aviso_privacidad": "Aviso de privacidad entregado",
    # Mensajes automáticos (recordatorios, felicitaciones) por WhatsApp o
    # correo: el paciente puede autorizarlos y retirarlos cuando quiera.
    "comunicaciones": "Recordatorios y mensajes por WhatsApp o correo",
}

CONSENT_METHODS: dict[str, str] = {
    "firma_presencial": "Firmado en la clínica",
    "verbal": "De palabra, en presencia del personal",
    "digital": "Por medio digital",
}

# Una vista repetida de la misma ficha por la misma persona dentro de este
# margen cuenta como un solo acceso: el registro debe responder "quién vio
# esta historia", no llenarse con cada recarga de pantalla.
ACCESS_DEDUP_MINUTES = 15

# Columnas que nunca salen en una exportación de datos: son credenciales o
# detalles internos del sistema, no datos del paciente.
EXPORT_EXCLUDED_COLUMNS = {"clinic_id", "token_hash", "hashed_password"}
