"""Datos de demostración para desarrollo: una clínica, catálogo de permisos,
roles base, un usuario administrador y un odontólogo.

Uso:
    python seed.py

Credenciales de desarrollo (NO usar en producción):
    admin@clinica-demo.test / Admin123!
    odontologo@clinica-demo.test / Odonto123!
"""

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.permissions import DEFAULT_ROLES, PERMISSION_CATALOG
from app.core.security import hash_password
from app.modules.clinics.models import Branch, Clinic, Operatory
from app.modules.medical_history.models import MedicalHistory
from app.modules.odontogram.models import Odontogram, ToothCondition
from app.modules.patients.models import Patient
from app.modules.professionals.models import Professional, Specialty
from app.modules.users.models import Permission, Role, User

ADMIN_EMAIL = "admin@clinicademo.com"
ADMIN_PASSWORD = "Admin123!"
DENTIST_EMAIL = "odontologo@clinicademo.com"
DENTIST_PASSWORD = "Odonto123!"


async def seed() -> None:
    async with async_session_factory() as db:
        existing = await db.execute(select(Clinic).where(Clinic.name == "Clínica Demo"))
        if existing.scalar_one_or_none() is not None:
            print("El seed ya fue aplicado (Clínica Demo ya existe). Nada que hacer.")
            return

        clinic = Clinic(
            name="Clínica Demo",
            legal_name="Clínica Demo S.A.",
            tax_id="0000000000001",
            address="Av. Principal 123",
            phone="+593999999999",
            email="contacto@clinica-demo.test",
            timezone="America/Guayaquil",
            currency="USD",
        )
        db.add(clinic)
        await db.flush()

        branch = Branch(clinic_id=clinic.id, name="Sede Principal", is_main=True, address=clinic.address)
        db.add(branch)
        await db.flush()

        db.add(Operatory(clinic_id=clinic.id, branch_id=branch.id, name="Consultorio 1"))
        db.add(Operatory(clinic_id=clinic.id, branch_id=branch.id, name="Consultorio 2"))

        # Catálogo global de permisos (idempotente: solo crea los que falten)
        existing_codes = {
            row[0] for row in (await db.execute(select(Permission.code))).all()
        }
        permission_by_code: dict[str, Permission] = {}
        for code, module, description in PERMISSION_CATALOG:
            if code in existing_codes:
                continue
            permission = Permission(code=code, module=module, description=description)
            db.add(permission)
            permission_by_code[code] = permission
        await db.flush()

        all_permissions = (await db.execute(select(Permission))).scalars().all()
        permission_by_code = {p.code: p for p in all_permissions}

        roles: dict[str, Role] = {}
        for role_name, codes in DEFAULT_ROLES.items():
            role = Role(
                clinic_id=clinic.id,
                name=role_name,
                description=f"Rol base: {role_name}",
                is_system=True,
                permissions=[permission_by_code[c] for c in codes],
            )
            db.add(role)
            roles[role_name] = role
        await db.flush()

        specialty = Specialty(clinic_id=clinic.id, name="Odontología general")
        db.add(specialty)
        await db.flush()

        admin_user = User(
            clinic_id=clinic.id,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            first_name="Administrador",
            last_name="Demo",
            is_superadmin=True,
            roles=[roles["Administrador"]],
        )
        db.add(admin_user)

        dentist_user = User(
            clinic_id=clinic.id,
            email=DENTIST_EMAIL,
            hashed_password=hash_password(DENTIST_PASSWORD),
            first_name="Odontólogo",
            last_name="Demo",
            roles=[roles["Odontólogo"]],
        )
        db.add(dentist_user)
        await db.flush()

        db.add(
            Professional(
                clinic_id=clinic.id,
                user_id=dentist_user.id,
                first_name=dentist_user.first_name,
                last_name=dentist_user.last_name,
                specialty_id=specialty.id,
                color_hex="#0F6FFF",
            )
        )

        patient_one = Patient(
            clinic_id=clinic.id,
            first_name="María",
            last_name="Gómez",
            national_id="0102030405",
            birth_date=date(1990, 4, 12),
            sex="F",
            phone="+593987654321",
            whatsapp="+593987654321",
            email="maria.gomez@example.com",
            address="Calle 10 y Av. Siempre Viva",
            city="Quito",
            occupation="Ingeniera",
            emergency_contact_name="Pedro Gómez",
            emergency_contact_phone="+593987654322",
        )
        patient_two = Patient(
            clinic_id=clinic.id,
            first_name="Carlos",
            last_name="Pérez",
            national_id="0607080910",
            birth_date=date(1985, 11, 3),
            sex="M",
            phone="+593912345678",
            city="Guayaquil",
        )
        db.add_all([patient_one, patient_two])
        await db.flush()

        db.add(
            MedicalHistory(
                clinic_id=clinic.id,
                patient_id=patient_one.id,
                created_by_id=dentist_user.id,
                created_at=datetime.now(timezone.utc),
                allergies="Penicilina",
                medications="Ninguno",
                medical_conditions="Ninguna conocida",
                habits="Bruxismo nocturno",
                chief_complaint="Sensibilidad al frío en molar inferior derecho",
                oral_hygiene="Buena",
                extraoral_exam="Sin hallazgos relevantes",
                intraoral_exam="Caries incipiente en pieza 46",
            )
        )

        first_odontogram = Odontogram(
            clinic_id=clinic.id,
            patient_id=patient_one.id,
            created_by_id=dentist_user.id,
            created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            conditions=[
                ToothCondition(clinic_id=clinic.id, fdi_number="46", surface="oclusal", condition="caries"),
                ToothCondition(clinic_id=clinic.id, fdi_number="36", surface="whole", condition="sellante"),
            ],
        )
        db.add(first_odontogram)
        await db.flush()

        db.add(
            Odontogram(
                clinic_id=clinic.id,
                patient_id=patient_one.id,
                created_by_id=dentist_user.id,
                created_at=datetime.now(timezone.utc),
                previous_odontogram_id=first_odontogram.id,
                conditions=[
                    ToothCondition(clinic_id=clinic.id, fdi_number="46", surface="oclusal", condition="restauracion"),
                    ToothCondition(clinic_id=clinic.id, fdi_number="36", surface="whole", condition="sellante"),
                    ToothCondition(clinic_id=clinic.id, fdi_number="18", surface="whole", condition="ausente"),
                ],
            )
        )

        await db.commit()

        print("Seed aplicado correctamente.")
        print(f"  Clínica: {clinic.name}")
        print(f"  Admin:      {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  Odontólogo: {DENTIST_EMAIL} / {DENTIST_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
