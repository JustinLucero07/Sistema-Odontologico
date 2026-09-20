APPOINTMENT_STATUSES: list[tuple[str, str]] = [
    ("programada", "Programada"),
    ("confirmada", "Confirmada"),
    ("en_espera", "En espera"),
    ("en_atencion", "En atención"),
    ("atendida", "Atendida"),
    ("cancelada", "Cancelada"),
    ("no_asistio", "No asistió"),
]
APPOINTMENT_STATUS_CODES = {code for code, _ in APPOINTMENT_STATUSES}

# A cancelled or no-show appointment frees its slot: it no longer blocks the
# professional's or the operatory's calendar.
SLOT_FREEING_STATUSES = {"cancelada", "no_asistio"}

REMINDER_CHANNELS: list[tuple[str, str]] = [
    ("whatsapp", "WhatsApp"),
    ("email", "Email"),
    ("sms", "SMS"),
]
REMINDER_CHANNEL_CODES = {code for code, _ in REMINDER_CHANNELS}

REMINDER_STATUSES = {"pendiente", "enviado", "fallido", "cancelado"}

# Reminders every appointment gets by default: one the day before, one a
# couple of hours ahead. Delivery itself belongs to the messaging phase — this
# module only schedules them.
DEFAULT_REMINDER_OFFSETS_MINUTES = [24 * 60, 120]
