"""Vocabulary of the dental laboratory module."""

LAB_ORDER_STATUSES: list[tuple[str, str]] = [
    ("borrador", "Borrador"),
    ("enviado", "Enviado al laboratorio"),
    ("en_proceso", "En proceso"),
    ("recibido", "Recibido en clínica"),
    ("probado", "Probado en el paciente"),
    ("instalado", "Instalado"),
    ("rechazado", "Rechazado / reenviado"),
    ("cancelado", "Cancelado"),
]
LAB_ORDER_STATUS_CODES = {code for code, _ in LAB_ORDER_STATUSES}

# An order moves forward through this chain. Going backwards is only allowed
# via "rechazado", which is itself a recorded event rather than an undo — a
# crown that came back from the lab wrong is a fact about the case.
STATUS_ORDER = ["borrador", "enviado", "en_proceso", "recibido", "probado", "instalado"]
TERMINAL_STATUSES = {"instalado", "cancelado"}

LAB_WORK_TYPES: list[tuple[str, str]] = [
    ("corona", "Corona"),
    ("puente", "Puente"),
    ("incrustacion", "Incrustación"),
    ("carilla", "Carilla"),
    ("protesis_total", "Prótesis total"),
    ("protesis_parcial", "Prótesis parcial removible"),
    ("ferula", "Férula de descarga"),
    ("guarda", "Guarda oclusal"),
    ("ortodoncia", "Aparato de ortodoncia"),
    ("modelo", "Modelo de estudio"),
    ("otro", "Otro trabajo"),
]
LAB_WORK_TYPE_CODES = {code for code, _ in LAB_WORK_TYPES}
