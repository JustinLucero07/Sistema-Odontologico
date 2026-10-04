"""Alta de un consultorio o clínica nueva (cliente), lista para trabajar y SIN
datos de demostración. Sirve igual para un odontólogo que trabaja solo que para
una clínica con equipo.

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
        [--odontologo --registro "MSP-12345"] [--sin-catalogo]

Con --odontologo, el administrador es también el profesional que atiende (el
caso de un consultorio de una persona): queda listo para agendar citas y
firmar recetas desde el primer día.

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
from app.modules.professionals.models import Professional, Specialty
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
            sys.exit(f"Ya existe un consultorio o clínica llamada «{args.nombre}».")

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

        especialidad = Specialty(clinic_id=clinic.id, name="Odontología general")
        db.add(especialidad)
        await db.flush()

        clave = _clave_temporal()
        fallos = problems(clave, email=email, names=(args.admin_nombre, args.admin_apellido))
        if fallos:  # no debería pasar, pero nunca se entrega una clave que el sistema rechazaría
            sys.exit("No se pudo generar una contraseña válida: " + "; ".join(fallos))

        admin = User(
            clinic_id=clinic.id,
            email=email,
            hashed_password=hash_password(clave),
            first_name=args.admin_nombre,
            last_name=args.admin_apellido,
            is_superadmin=False,
            must_change_password=True,
            roles=[roles["Administrador"]],
        )
        db.add(admin)
        await db.flush()

        if args.odontologo:
            db.add(
                Professional(
                    clinic_id=clinic.id,
                    user_id=admin.id,
                    first_name=args.admin_nombre,
                    last_name=args.admin_apellido,
                    specialty_id=especialidad.id,
                    license_number=args.registro,
                    color_hex="#0D7F76",
                )
            )

        if not args.sin_catalogo:
            for nombre, precio in CATALOGO_INICIAL:
                db.add(Treatment(clinic_id=clinic.id, name=nombre, default_price=precio))

        await db.commit()

    print()
    print(f"  Creado: {args.nombre}")
    if args.odontologo:
        print("  El administrador también quedó como profesional (listo para agendar).")
    print(f"  Usuario administrador: {email}")
    print(f"  Contraseña temporal:   {clave}")
    print()
    print("  Entréguela por un canal seguro. Se pedirá cambiarla en el primer ingreso.")
    print("  Esta es la única vez que se muestra.")
    print()


def main() -> None:
    p = argparse.ArgumentParser(description="Alta de un consultorio o clínica, sin datos de demostración.")
    p.add_argument("--nombre", required=True, help="Nombre comercial del consultorio o clínica")
    p.add_argument("--admin-email", required=True)
    p.add_argument("--admin-nombre", required=True)
    p.add_argument("--admin-apellido", required=True)
    p.add_argument("--razon-social")
    p.add_argument("--ruc")
    p.add_argument("--telefono")
    p.add_argument("--direccion")
    p.add_argument("--zona", default="America/Guayaquil", help="Zona horaria (IANA)")
    p.add_argument("--odontologo", action="store_true", help="El administrador también atiende pacientes")
    p.add_argument("--registro", help="Registro profesional del odontólogo (sale en las recetas)")
    p.add_argument("--sin-catalogo", action="store_true", help="No cargar el catálogo inicial de tratamientos")
    asyncio.run(crear(p.parse_args()))


if __name__ == "__main__":
    main()
