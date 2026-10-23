"""Restablece la contraseña de un usuario cuando nadie en la clínica puede
hacerlo (por ejemplo, el odontólogo que trabaja solo y es el único
administrador). Genera una clave temporal, obliga a cambiarla al entrar y
cierra las sesiones abiertas. Queda en la auditoría.

    python restablecer_clave.py correo@consultorio.com
    (en el servidor: odonto restablecer-clave correo@consultorio.com)
"""
import asyncio
import secrets
import string
import sys

from sqlalchemy import func, select

from app.core.audit import record_audit
from app.core.database import async_session_factory
from app.core.models_registry import *  # noqa: F401,F403
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.service import _revoke_sessions


def _clave() -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        c = "".join(secrets.choice(alfabeto) for _ in range(12))
        if any(x.isdigit() for x in c) and any(x.isalpha() for x in c):
            return c


async def main(correo: str) -> None:
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(func.lower(User.email) == correo.strip().lower()))).scalar_one_or_none()
        if user is None:
            sys.exit(f"No existe un usuario con el correo {correo}.")
        clave = _clave()
        user.hashed_password = hash_password(clave)
        user.must_change_password = True
        user.is_active = True
        await _revoke_sessions(db, user.id)
        await record_audit(db, clinic_id=user.clinic_id, user_id=None, action="reset_password_cli",
                           entity_type="user", entity_id=str(user.id))
        await db.commit()
    print(f"\n  Contraseña temporal para {correo}: {clave}\n  Se pedirá cambiarla en el primer ingreso. Entréguela por un canal seguro.\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python restablecer_clave.py correo@consultorio.com")
    asyncio.run(main(sys.argv[1]))
