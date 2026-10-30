"""Retoma las facturas y notas de crédito que aún no terminan con el SRI
(pendientes de envío o esperando autorización), de TODAS las clínicas.

    python procesar_facturas.py            # una pasada
    python procesar_facturas.py --cada 1   # en bucle, cada minuto

Lo corre el servicio «facturador» de producción. Es seguro repetirlo: un
comprobante autorizado o rechazado no se vuelve a tocar, y el SRI reconoce un
reenvío por su clave de acceso.
"""

import argparse
import asyncio
import signal
from datetime import datetime

from app.core.database import async_session_factory
from app.core.models_registry import *  # noqa: F401,F403
from app.modules.invoicing.service import process_due


async def una_pasada() -> None:
    async with async_session_factory() as db:
        n = await process_due(db)
        if n:
            print(f"{datetime.now():%Y-%m-%d %H:%M} {n} comprobante(s) procesados con el SRI", flush=True)


async def bucle(minutos: int) -> None:
    parar = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(s, parar.set)
    print(f"Facturador: revisando cada {minutos} minuto(s).", flush=True)
    while not parar.is_set():
        try:
            await una_pasada()
        except Exception as e:  # un fallo puntual (red, base) no debe detener el servicio
            print(f"{datetime.now():%Y-%m-%d %H:%M} error: {e}", flush=True)
        try:
            await asyncio.wait_for(parar.wait(), timeout=minutos * 60)
        except asyncio.TimeoutError:
            pass


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cada", type=int, default=0, help="minutos entre pasadas (0 = una sola)")
    a = p.parse_args()
    asyncio.run(bucle(a.cada) if a.cada else una_pasada())


if __name__ == "__main__":
    main()
