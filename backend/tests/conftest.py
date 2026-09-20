import asyncio
import os

# Points at the Postgres from infra/docker-compose.yml (published on 5434 to
# avoid clashing with a local Postgres on the default port). Override with
# TEST_DATABASE_URL to run the suite against a different database.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://odonto:odonto@localhost:5434/odonto_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models_registry  # noqa: F401
from app.core.database import Base, get_db
from app.core.permissions import DEFAULT_ROLES, PERMISSION_CATALOG
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.main import app
from app.modules.clinics.models import Clinic
from app.modules.users.models import Permission, Role, User

# Kept in sync with the Phase 5 migration.
EXCLUSION_CONSTRAINTS = [
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    """
    ALTER TABLE appointments
    ADD CONSTRAINT appointments_no_professional_overlap
    EXCLUDE USING gist (
        professional_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    )
    WHERE (status NOT IN ('cancelada', 'no_asistio'))
    """,
    """
    ALTER TABLE appointments
    ADD CONSTRAINT appointments_no_operatory_overlap
    EXCLUDE USING gist (
        operatory_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    )
    WHERE (operatory_id IS NOT NULL AND status NOT IN ('cancelada', 'no_asistio'))
    """,
]


def _prepare_schema_sync() -> None:
    """Runs in its own throwaway asyncio loop (asyncio.run), fully outside
    pytest-asyncio's loop management, so it can never leak an asyncpg
    connection bound to a loop that later gets closed."""

    async def _run() -> None:
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            # create_all cannot express the appointment exclusion constraints
            # (they live as raw SQL in the migration), so mirror them here —
            # otherwise the tests would run against a schema that allows the
            # double bookings production rejects.
            for statement in EXCLUSION_CONSTRAINTS:
                await conn.exec_driver_sql(statement)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            for code, module, description in PERMISSION_CATALOG:
                session.add(Permission(code=code, module=module, description=description))
            await session.commit()

        await engine.dispose()

    asyncio.run(_run())


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    """Global permission catalog + schema, seeded once for the whole run —
    mirrors how it is seeded once per real deployment."""
    _prepare_schema_sync()
    yield


@pytest.fixture
async def test_engine():
    # Created fresh inside each test's own event loop (function-scoped under
    # asyncio_mode=auto) — sharing one asyncpg connection across event loops
    # is what caused "attached to a different loop" errors earlier.
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_connection(test_engine):
    async with test_engine.connect() as connection:
        await connection.begin()
        yield connection
        await connection.rollback()


@pytest.fixture
def session_factory(db_connection):
    """Sessions bound to one connection/transaction for the whole test. Any
    session.commit() the app code issues only releases a SAVEPOINT — the
    outer transaction is rolled back in db_connection's teardown, so every
    test starts from the same clean, already-migrated schema without paying
    for drop/create per test."""
    return async_sessionmaker(bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint")


@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
async def clinic_with_users(db_session):
    """A clinic with the default role catalog plus one admin and one dentist
    user — mirrors seed.py at a smaller scale for test isolation."""
    clinic = Clinic(name="Clínica Test")
    db_session.add(clinic)
    await db_session.flush()

    existing_permissions = (await db_session.execute(select(Permission))).scalars().all()
    permission_by_code = {p.code: p for p in existing_permissions}

    roles = {}
    for role_name, codes in DEFAULT_ROLES.items():
        role = Role(
            clinic_id=clinic.id, name=role_name, is_system=True,
            permissions=[permission_by_code[c] for c in codes],
        )
        db_session.add(role)
        roles[role_name] = role
    await db_session.flush()

    admin = User(
        clinic_id=clinic.id, email="admin@clinicatest.io", hashed_password=hash_password("Admin123!"),
        first_name="Admin", last_name="Test", roles=[roles["Administrador"]],
    )
    dentist = User(
        clinic_id=clinic.id, email="dentist@clinicatest.io", hashed_password=hash_password("Dentist123!"),
        first_name="Dentist", last_name="Test", roles=[roles["Odontólogo"]],
    )
    db_session.add_all([admin, dentist])
    await db_session.flush()
    await db_session.commit()

    return {"clinic": clinic, "admin": admin, "dentist": dentist, "roles": roles}


@pytest.fixture
async def client(session_factory, clinic_with_users):
    # The login rate limiter's storage is a process-wide singleton, so without
    # a reset per test it accumulates across the whole suite (every request
    # comes from the same test-client "IP") and starts 429-ing unrelated tests.
    limiter.reset()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
