"""Envía los recordatorios de citas que ya tocan, para TODAS las clínicas.

Es lo mismo que el endpoint POST /messaging/dispatch, pero sin necesitar un
usuario ni un token: lo corre el servicio «recordatorios» de producción.

    python despachar_recordatorios.py            # una pasada
    python despachar_recordatorios.py --cada 15  # en bucle, cada 15 minutos

Es seguro repetirlo: un recordatorio ya resuelto nunca se vuelve a enviar.
"""

import argparse
import asyncio
import signal
from datetime import datetime

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.models_registry import *  # noqa: F401,F403
from app.modules.clinics.models import Clinic
from app.modules.messaging.service import dispatch_due_reminders


async def una_pasada() -> None:
    async with async_session_factory() as db:
        clinicas = (await db.execute(select(Clinic.id, Clinic.name))).all()
        for clinic_id, nombre in clinicas:
            r = await dispatch_due_reminders(db, clinic_id)
            await db.commit()
            if r.due:
                print(
                    f"{datetime.now():%Y-%m-%d %H:%M} {nombre}: {r.due} pendientes · "
                    f"{r.sent} enviados · {r.simulated} simulados · {r.failed} fallidos · {r.skipped} omitidos",
                    flush=True,
                )


async def bucle(minutos: int) -> None:
    parar = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(s, parar.set)
    print(f"Recordatorios: revisando cada {minutos} minutos.", flush=True)
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
