"""Production guards and response hardening.

Two jobs:

  1. **Refuse to start a production server that is unsafe.** Every item below
     is a mistake somebody makes exactly once, in the dark, at a customer's
     site. A crash on boot with a clear message costs an hour; a system that
     starts happily with the default signing key costs the whole database.

  2. **Set the security headers a browser respects.** They are cheap, and each
     one closes a class of attack that the application code cannot.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import Settings

logger = logging.getLogger(__name__)

INSECURE_JWT_SECRETS = {"change-me-in-production", "secret", "changeme", ""}


class UnsafeProductionConfig(RuntimeError):
    """Raised at startup. Deliberately fatal: a warning in a log nobody reads
    is not a safety mechanism."""


def check_production_config(settings: Settings) -> list[str]:
    """Returns the problems found. Empty means the configuration is safe to
    serve real patients from."""
    problems: list[str] = []

    if settings.JWT_SECRET_KEY in INSECURE_JWT_SECRETS:
        problems.append(
            "JWT_SECRET_KEY sigue siendo el valor por defecto. Cualquiera que conozca "
            "este proyecto podría firmar tokens válidos. Genere uno con "
            "`python -c \"import secrets; print(secrets.token_urlsafe(64))\"`."
        )
    elif len(settings.JWT_SECRET_KEY) < 32:
        problems.append("JWT_SECRET_KEY es demasiado corto: use al menos 32 caracteres.")

    if not settings.REFRESH_TOKEN_COOKIE_SECURE:
        problems.append(
            "REFRESH_TOKEN_COOKIE_SECURE está desactivado: la cookie de refresco viajaría "
            "por HTTP en claro."
        )

    if "*" in settings.CORS_ORIGINS:
        problems.append(
            "CORS_ORIGINS incluye '*'. Con credenciales habilitadas, cualquier sitio "
            "podría hacer peticiones autenticadas en nombre del usuario."
        )

    insecure_origins = [o for o in settings.CORS_ORIGINS if o.startswith("http://")
                        and "localhost" not in o and "127.0.0.1" not in o]
    if insecure_origins:
        problems.append(f"CORS_ORIGINS contiene orígenes sin TLS: {', '.join(insecure_origins)}")

    if settings.DATABASE_URL.endswith("odonto:odonto@localhost:5432/odonto"):
        problems.append("DATABASE_URL sigue apuntando a la base de desarrollo con credenciales por defecto.")

    if settings.STORAGE_PROVIDER == "local" and settings.STORAGE_LOCAL_PATH.startswith("./"):
        problems.append(
            "STORAGE_LOCAL_PATH es una ruta relativa: las radiografías se guardarían junto "
            "al código y se perderían al redesplegar."
        )

    return problems


def enforce_production_config(settings: Settings) -> None:
    if settings.ENV != "production":
        # Outside production the same checks run, but only to inform: a
        # developer should see what would block a release, not be stopped.
        for problem in check_production_config(settings):
            logger.info("[config] pendiente para producción: %s", problem)
        return

    problems = check_production_config(settings)
    if problems:
        raise UnsafeProductionConfig(
            "El servidor no puede arrancar en producción con esta configuración:\n  - "
            + "\n  - ".join(problems)
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers on every response.

    The CSP is deliberately strict and applies to API responses, which never
    need to load anything. The SPA is served by nginx, which sets its own."""

    def __init__(self, app, *, https_only: bool = False):
        super().__init__(app)
        self.https_only = https_only

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = response.headers

        # A browser must not second-guess our content types: sniffing is how a
        # stored file gets executed as a script.
        headers.setdefault("X-Content-Type-Options", "nosniff")
        # Nothing here is ever legitimately framed.
        headers.setdefault("X-Frame-Options", "DENY")
        # A portal token lives in the URL, so referrers must not leak it to
        # whatever the patient clicks next.
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"
        )
        headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        # Clinical responses must not sit in a shared cache.
        if request.url.path.startswith("/api/"):
            headers.setdefault("Cache-Control", "no-store")

        if self.https_only:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
