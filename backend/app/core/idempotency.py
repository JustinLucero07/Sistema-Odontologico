"""Reintentos seguros: la cabecera Idempotency-Key.

La app del celular guarda los cambios hechos sin conexión y los reenvía al
volver la red. Si la red se cortó justo DESPUÉS de que el servidor guardara un
cambio, el teléfono no se entera y lo vuelve a mandar. Con la misma llave, el
servidor no lo repite: devuelve la respuesta que ya dio. Así un paciente o una
cita nunca se crean dos veces.

Las respuestas se guardan 24 h en Redis, separadas por usuario (la llave sola
no sirve para leer la respuesta de otra persona). Sin Redis disponible, las
peticiones pasan normalmente: se pierde la protección, no el servicio.
"""

import hashlib
import json
import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.security import decode_token

logger = logging.getLogger(__name__)

METODOS = {b"POST", b"PUT", b"PATCH", b"DELETE"}
DURACION = 24 * 3600
MAX_CUERPO = 1_000_000


class IdempotencyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._redis = None
        self._sin_redis = False

    async def _cliente(self):
        if self._sin_redis:
            return None
        if self._redis is None:
            try:
                from redis import asyncio as aioredis

                self._redis = aioredis.from_url(get_settings().REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
                await self._redis.ping()
            except Exception as e:  # sin Redis se sigue funcionando
                logger.warning("Idempotencia desactivada: Redis no disponible (%s)", e)
                self._redis = None
                self._sin_redis = True
                return None
        return self._redis

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"].encode() not in METODOS:
            return await self.app(scope, receive, send)
        cabeceras = dict(scope.get("headers") or [])
        llave = cabeceras.get(b"idempotency-key", b"").decode()[:100]
        autorizacion = cabeceras.get(b"authorization", b"").decode()
        if not llave or not autorizacion.lower().startswith("bearer "):
            return await self.app(scope, receive, send)
        try:
            usuario = decode_token(autorizacion[7:]).get("sub", "")
        except Exception:
            return await self.app(scope, receive, send)
        redis = await self._cliente()
        if redis is None:
            return await self.app(scope, receive, send)

        clave = "idem:" + hashlib.sha256(f"{usuario}|{llave}|{scope['method']}|{scope['path']}".encode()).hexdigest()
        try:
            guardada = await redis.get(clave)
        except Exception:
            guardada = None
        if guardada:
            r = json.loads(guardada)
            await send({
                "type": "http.response.start",
                "status": r["status"],
                "headers": [(b"content-type", r["type"].encode()), (b"idempotent-replay", b"true")],
            })
            await send({"type": "http.response.body", "body": r["body"].encode("latin-1")})
            return

        estado = {"status": 500, "type": "application/json", "partes": [], "tam": 0}

        async def enviar(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                estado["status"] = mensaje["status"]
                for k, v in mensaje.get("headers", []):
                    if k.lower() == b"content-type":
                        estado["type"] = v.decode()
            elif mensaje["type"] == "http.response.body":
                cuerpo = mensaje.get("body", b"")
                estado["tam"] += len(cuerpo)
                if estado["tam"] <= MAX_CUERPO:
                    estado["partes"].append(cuerpo)
            await send(mensaje)

        await self.app(scope, receive, enviar)
        # Solo se recuerda lo que el servidor resolvió: un 5xx se puede reintentar.
        if estado["status"] < 500 and estado["tam"] <= MAX_CUERPO:
            try:
                await redis.set(
                    clave,
                    json.dumps({"status": estado["status"], "type": estado["type"], "body": b"".join(estado["partes"]).decode("latin-1")}),
                    ex=DURACION,
                )
            except Exception as e:
                logger.warning("No se pudo guardar la respuesta idempotente: %s", e)
