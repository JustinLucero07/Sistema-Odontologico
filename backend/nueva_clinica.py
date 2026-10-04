"""Alta de una clínica nueva (cliente), lista para trabajar y SIN datos de
demostración.

Crea la clínica con su sede y consultorio, los roles base con todos los
permisos, el usuario administrador (que deberá cambiar la contraseña temporal
al entrar) y un catálogo inicial de tratamientos con precios orientativos que la
clínica ajusta desde Configuración → Tratamientos.

Uso:
    python nueva_clinica.py \\
        --nombre "Clínica Dental Sonrisa" \\
        --admin-email dra.perez@sonrisa.ec \\
        --admin-nombre "Ana" --admin-apellido "Pérez" \\
        [--ruc 1790000000001] [--telefono "+593 99 999 9999"] \\
        [--direccion "Av. Amazonas N24"] [--zona America/Guayaquil] \\
        [--sin-catalogo]

Imprime la contraseña temporal UNA sola vez. Entréguela al cliente por un
canal seguro; el sistema le obligará a cambiarla en su primer ingreso.
"""

import argparse
import asyncio
import secrets
import string
import sys

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.core.models_registry import *  # noqa: F401,F403  (registra todos los modelos)
from app.core.password_policy import problems
from app.core.permissions import DEFAULT_ROLES, PERMISSION_CATALOG
from app.core.security import hash_password
from app.modules.clinics.models import Branch, Clinic, Operatory
from app.modules.professionals.models import Specialty
from app.modules.treatments.models import Treatment
from app.modules.users.models import Permission, Role, User

# Precios orientativos (USD). Son un punto de partida para no empezar con el
# catálogo vacío; cada clínica pone los suyos.
CATALOGO_INICIAL: list[tuple[str, float]] = [
    ("Consulta y diagnóstico", 20),
    ("Profilaxis (limpieza)", 30),
    ("Destartraje", 40),
    ("Aplicación de flúor", 15),
    ("Sellante por pieza", 20),
    ("Resina simple", 35),
    ("Resina compuesta", 45),
    ("Endodoncia unirradicular", 120),
    ("Endodoncia multirradicular", 180),
    ("Extracción simple", 35),
    ("Extracción de tercer molar", 120),
    ("Corona de porcelana", 250),
    ("Corona de zirconio", 380),
    ("Prótesis parcial removible", 300),
    ("Prótesis total", 450),
    ("Blanqueamiento", 180),
    ("Radiografía periapical", 10),
    ("Radiografía panorámica", 25),
    ("Ortodoncia (control mensual)", 50),
    ("Implante dental", 900),
]


def _clave_temporal() -> str:
    """12 caracteres con letras y números, que cumple la política."""
    alfabeto = string.ascii_letters + string.digits
    while True:
        clave = "".join(secrets.choice(alfabeto) for _ in range(12))
        if any(c.isdigit() for c in clave) and any(c.isalpha() for c in clave):
            return clave


async def crear(args: argparse.Namespace) -> None:
    async with async_session_factory() as db:
        email = args.admin_email.strip().lower()
        if await db.scalar(select(func.count(User.id)).where(func.lower(User.email) == email)):
            sys.exit(f"Ya existe un usuario con el correo {email}.")
        if await db.scalar(select(func.count(Clinic.id)).where(Clinic.name == args.nombre)):
            sys.exit(f"Ya existe una clínica llamada «{args.nombre}».")

        clinic = Clinic(
            name=args.nombre,
            legal_name=args.razon_social or args.nombre,
            tax_id=args.ruc,
            address=args.direccion,
            phone=args.telefono,
            email=email,
            timezone=args.zona,
            currency="USD",
        )
        db.add(clinic)
        await db.flush()

        branch = Branch(clinic_id=clinic.id, name="Sede principal", is_main=True, address=args.direccion)
        db.add(branch)
        await db.flush()
        db.add(Operatory(clinic_id=clinic.id, branch_id=branch.id, name="Consultorio 1"))

        # Catálogo global de permisos (solo agrega los que falten).
        existentes = {row[0] for row in (await db.execute(select(Permission.code))).all()}
        for code, module, description in PERMISSION_CATALOG:
            if code not in existentes:
                db.add(Permission(code=code, module=module, description=description))
        await db.flush()
        por_codigo = {p.code: p for p in (await db.execute(select(Permission))).scalars().all()}

        roles: dict[str, Role] = {}
        for nombre_rol, codigos in DEFAULT_ROLES.items():
            rol = Role(
                clinic_id=clinic.id,
                name=nombre_rol,
                description=f"Rol base: {nombre_rol}",
                is_system=True,
                permissions=[por_codigo[c] for c in codigos],
            )
            db.add(rol)
            roles[nombre_rol] = rol
        await db.flush()

        db.add(Specialty(clinic_id=clinic.id, name="Odontología general"))

        clave = _clave_temporal()
        fallos = problems(clave, email=email, names=(args.admin_nombre, args.admin_apellido))
        if fallos:  # no debería pasar, pero nunca se entrega una clave que el sistema rechazaría
            sys.exit("No se pudo generar una contraseña válida: " + "; ".join(fallos))

        db.add(
            User(
                clinic_id=clinic.id,
                email=email,
                hashed_password=hash_password(clave),
                first_name=args.admin_nombre,
                last_name=args.admin_apellido,
                is_superadmin=False,
                must_change_password=True,
                roles=[roles["Administrador"]],
            )
        )

        if not args.sin_catalogo:
            for nombre, precio in CATALOGO_INICIAL:
                db.add(Treatment(clinic_id=clinic.id, name=nombre, default_price=precio))

        await db.commit()

    print()
    print(f"  Clínica creada: {args.nombre}")
    print(f"  Usuario administrador: {email}")
    print(f"  Contraseña temporal:   {clave}")
    print()
    print("  Entréguela por un canal seguro. Se pedirá cambiarla en el primer ingreso.")
    print("  Esta es la única vez que se muestra.")
    print()


def main() -> None:
    p = argparse.ArgumentParser(description="Alta de una clínica nueva, sin datos de demostración.")
    p.add_argument("--nombre", required=True, help="Nombre comercial de la clínica")
    p.add_argument("--admin-email", required=True)
    p.add_argument("--admin-nombre", required=True)
    p.add_argument("--admin-apellido", required=True)
    p.add_argument("--razon-social")
    p.add_argument("--ruc")
    p.add_argument("--telefono")
    p.add_argument("--direccion")
    p.add_argument("--zona", default="America/Guayaquil", help="Zona horaria (IANA)")
    p.add_argument("--sin-catalogo", action="store_true", help="No cargar el catálogo inicial de tratamientos")
    asyncio.run(crear(p.parse_args()))


if __name__ == "__main__":
    main()
