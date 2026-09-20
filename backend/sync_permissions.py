"""Bring every clinic's system roles up to date with the permission catalog.

`seed.py` only runs once, on an empty database. Every phase since has added
permission codes, so a clinic seeded at phase 4 has an "Administrador" role
that silently lacks the phase 7 modules — the tabs simply never appear, with
no error anywhere to explain why.

This script is additive and idempotent: it inserts catalog codes the database
is missing and grants each system role the codes `DEFAULT_ROLES` says it
should have. It never REVOKES anything, because a permission a clinic's admin
deliberately removed from a role is a decision, not drift.

    python sync_permissions.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_factory
from app.core.models_registry import *  # noqa: F401,F403  (registers every model)
from app.core.permissions import DEFAULT_ROLES, PERMISSION_CATALOG
from app.modules.users.models import Permission, Role


async def sync() -> None:
    async with async_session_factory() as db:
        existing = {row[0] for row in (await db.execute(select(Permission.code))).all()}
        added_codes = []
        for code, module, description in PERMISSION_CATALOG:
            if code in existing:
                continue
            db.add(Permission(code=code, module=module, description=description))
            added_codes.append(code)
        await db.flush()

        by_code = {p.code: p for p in (await db.execute(select(Permission))).scalars().all()}

        roles = (
            (await db.execute(select(Role).options(selectinload(Role.permissions))))
            .scalars()
            .all()
        )

        granted_total = 0
        for role in roles:
            wanted = DEFAULT_ROLES.get(role.name)
            if wanted is None:
                continue  # A custom role belongs to whoever made it.
            held = {p.code for p in role.permissions}
            missing = [c for c in wanted if c not in held and c in by_code]
            for code in missing:
                role.permissions.append(by_code[code])
            if missing:
                granted_total += len(missing)
                print(f"  {role.name} (clínica {role.clinic_id}): +{len(missing)} permisos")
                for code in missing:
                    print(f"      {code}")

        await db.commit()

    print()
    print(f"Permisos nuevos en el catálogo: {len(added_codes)}")
    if added_codes:
        print("  " + ", ".join(added_codes))
    print(f"Concesiones añadidas a roles: {granted_total}")
    if granted_total:
        print("Los usuarios afectados deben volver a iniciar sesión.")


if __name__ == "__main__":
    asyncio.run(sync())
