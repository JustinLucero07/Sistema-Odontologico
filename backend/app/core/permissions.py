"""Global permission catalog. New modules add codes here as they ship — the
mechanism (code string on a role) never changes, so later phases never require
an RBAC schema migration, only new rows."""

PERMISSION_CATALOG: list[tuple[str, str, str]] = [
    # (code, module, description)
    ("patients:read", "patients", "Ver pacientes"),
    ("patients:write", "patients", "Crear/editar pacientes"),
    ("patients:delete", "patients", "Eliminar (baja) pacientes"),
    ("medical_history:read", "medical_history", "Ver historia clínica"),
    ("medical_history:write", "medical_history", "Modificar historia clínica"),
    ("odontogram:read", "odontogram", "Ver odontograma"),
    ("odontogram:write", "odontogram", "Modificar odontograma"),
    ("diagnoses:read", "diagnoses", "Ver diagnósticos"),
    ("diagnoses:write", "diagnoses", "Crear/editar diagnósticos"),
    ("treatments:read", "treatments", "Ver catálogo de tratamientos y planes de tratamiento"),
    ("treatments:write", "treatments", "Crear/editar catálogo de tratamientos y planes"),
    ("budgets:read", "budgets", "Ver presupuestos"),
    ("budgets:write", "budgets", "Crear/editar presupuestos"),
    ("appointments:read", "appointments", "Ver agenda y citas"),
    ("appointments:write", "appointments", "Crear/editar citas"),
    ("payments:read", "payments", "Ver pagos y facturación"),
    ("payments:write", "payments", "Registrar pagos"),
    ("reports:read", "reports", "Ver reportes"),
    ("inventory:read", "inventory", "Ver inventario"),
    ("inventory:write", "inventory", "Administrar inventario"),
    ("laboratory:read", "laboratory", "Ver trabajos de laboratorio"),
    ("laboratory:write", "laboratory", "Administrar trabajos de laboratorio"),
    ("users:manage", "system", "Administrar usuarios"),
    ("roles:manage", "system", "Administrar roles y permisos"),
    ("settings:manage", "system", "Administrar configuración de la clínica"),
    ("audit:read", "system", "Ver auditoría"),
]

DEFAULT_ROLES: dict[str, list[str]] = {
    "Administrador": [code for code, _, _ in PERMISSION_CATALOG],
    "Odontólogo": [
        "patients:read", "patients:write",
        "medical_history:read", "medical_history:write",
        "odontogram:read", "odontogram:write",
        "diagnoses:read", "diagnoses:write",
        "treatments:read", "treatments:write",
        "budgets:read", "budgets:write",
        "appointments:read", "appointments:write",
    ],
    "Recepción": [
        "patients:read", "patients:write",
        "medical_history:read",
        "treatments:read",
        "appointments:read", "appointments:write",
        "payments:read", "payments:write",
        "budgets:read",
    ],
    "Asistente dental": [
        "patients:read",
        "odontogram:read",
        "diagnoses:read",
        "treatments:read",
        "appointments:read",
    ],
    "Contabilidad": [
        "payments:read", "payments:write",
        "reports:read",
    ],
}
