"""Phase 12: hardening.

Nothing here adds a feature. These tests check the things that only matter on
the day something goes wrong: that an unsafe production config refuses to
start, that the browser gets the headers it needs, and that an account under
attack locks itself.
"""

import pytest

from app.core.config import Settings
from app.core.hardening import (
    SecurityHeadersMiddleware,
    UnsafeProductionConfig,
    check_production_config,
    enforce_production_config,
)


def _production(**overrides) -> Settings:
    base = dict(
        ENV="production",
        JWT_SECRET_KEY="x" * 64,
        REFRESH_TOKEN_COOKIE_SECURE=True,
        CORS_ORIGINS=["https://clinica.example"],
        DATABASE_URL="postgresql+asyncpg://real:sN4kePass@db.internal:5432/odonto",
        STORAGE_LOCAL_PATH="/var/lib/odonto/storage",
    )
    base.update(overrides)
    return Settings(**base)


# ---- Production config guard -------------------------------------------


def test_a_safe_production_config_passes():
    assert check_production_config(_production()) == []
    enforce_production_config(_production())  # must not raise


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"JWT_SECRET_KEY": "change-me-in-production"}, "JWT_SECRET_KEY"),
        ({"JWT_SECRET_KEY": "corto"}, "demasiado corto"),
        ({"REFRESH_TOKEN_COOKIE_SECURE": False}, "REFRESH_TOKEN_COOKIE_SECURE"),
        ({"CORS_ORIGINS": ["*"]}, "'*'"),
        ({"CORS_ORIGINS": ["http://clinica.example"]}, "sin TLS"),
        ({"STORAGE_LOCAL_PATH": "./storage"}, "ruta relativa"),
    ],
)
def test_each_unsafe_setting_is_caught(overrides, expected):
    problems = check_production_config(_production(**overrides))
    assert any(expected in p for p in problems), problems


def test_production_refuses_to_start_when_unsafe():
    """Fatal on purpose: a warning in a log nobody reads is not a safety
    mechanism."""
    with pytest.raises(UnsafeProductionConfig) as exc:
        enforce_production_config(_production(JWT_SECRET_KEY="change-me-in-production"))
    assert "no puede arrancar" in str(exc.value)


def test_development_only_informs():
    """A developer should see what would block a release, not be stopped."""
    unsafe = _production(ENV="development", JWT_SECRET_KEY="change-me-in-production")
    assert check_production_config(unsafe)  # the problem is still detected
    enforce_production_config(unsafe)  # but it does not raise


# ---- Security headers ---------------------------------------------------


async def test_every_response_carries_the_security_headers(client, clinic_with_users):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clinicatest.io", "password": "Admin123!"},
    )
    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    # A portal token lives in the URL; referrers must not leak it onward.
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    # Clinical responses must not sit in a shared cache.
    assert headers["Cache-Control"] == "no-store"


async def test_hsts_is_only_sent_over_https(client, clinic_with_users):
    """Sending HSTS from a plain-HTTP dev server would pin the developer's
    browser to https://localhost and break it for everything else."""
    response = await client.get("/health")
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_is_sent_in_production():
    middleware = SecurityHeadersMiddleware(app=None, https_only=True)
    assert middleware.https_only is True


# ---- Login lockout ------------------------------------------------------


async def test_an_account_locks_after_repeated_failures(client, clinic_with_users):
    """The per-IP rate limit does not cover a distributed attempt against ONE
    account, which is the shape an attack on a known email takes."""
    from app.modules.auth.service import MAX_FAILED_LOGINS

    body = {"email": "admin@clinicatest.io", "password": "contraseña-equivocada"}
    for _ in range(MAX_FAILED_LOGINS):
        response = await client.post("/api/v1/auth/login", json=body)
        assert response.status_code == 401

    # The next attempt is refused as locked, not merely as wrong.
    locked = await client.post("/api/v1/auth/login", json=body)
    assert locked.status_code == 429
    assert "bloqueada" in locked.json()["detail"].lower()

    # And the RIGHT password is refused too, otherwise the lock is theatre.
    correct = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clinicatest.io", "password": "Admin123!"},
    )
    assert correct.status_code == 429


async def test_a_successful_login_clears_the_counter(client, clinic_with_users, db_session):
    from sqlalchemy import select

    from app.modules.users.models import User

    for _ in range(3):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@clinicatest.io", "password": "mal"},
        )
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clinicatest.io", "password": "Admin123!"},
    )
    assert ok.status_code == 200

    user = (
        await db_session.execute(select(User).where(User.email == "admin@clinicatest.io"))
    ).scalar_one()
    await db_session.refresh(user)
    assert user.failed_login_count == 0
    assert user.locked_until is None


async def test_a_wrong_password_and_an_unknown_email_look_the_same(client, clinic_with_users):
    """Saying 'that account exists but the password was wrong' tells an
    attacker which emails are real."""
    unknown = await client.post(
        "/api/v1/auth/login",
        json={"email": "nadie@clinicatest.io", "password": "loquesea"},
    )
    wrong = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clinicatest.io", "password": "loquesea"},
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
