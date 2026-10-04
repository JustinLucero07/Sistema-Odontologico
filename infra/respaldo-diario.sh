#!/bin/sh
# Respaldo diario dentro del contenedor «respaldos».
# Cada día a la HORA_RESPALDO: volcado de la base (formato custom de pg_dump,
# se restaura con pg_restore) y copia de los archivos clínicos. Borra los
# respaldos con más de RETENCION_DIAS días.
set -eu
# Como proceso principal del contenedor, sh ignora SIGTERM salvo que se
# atienda: sin esto «docker compose down» esperaría y lo mataría a la fuerza.
trap 'echo "Respaldos detenidos."; exit 0' TERM INT
mkdir -p /respaldos
echo "Respaldos activos: cada día a las ${HORA_RESPALDO}:00, retención ${RETENCION_DIAS} días."
while true; do
  if [ "$(date +%H)" = "${HORA_RESPALDO}" ]; then
    SELLO=$(date +%Y%m%d-%H%M%S)
    if pg_dump -h postgres -U odonto -d odonto -Fc -f "/respaldos/odonto-${SELLO}.dump"; then
      tar -czf "/respaldos/archivos-${SELLO}.tar.gz" -C /storage . 2>/dev/null || true
      # Verificación mínima: el volcado se puede leer y lista tablas.
      if pg_restore -l "/respaldos/odonto-${SELLO}.dump" | grep -q "TABLE DATA public patients"; then
        echo "$(date) respaldo OK: odonto-${SELLO}.dump"
      else
        mv "/respaldos/odonto-${SELLO}.dump" "/respaldos/odonto-${SELLO}.dump.SOSPECHOSO"
        echo "$(date) ATENCIÓN: el respaldo no contiene la tabla de pacientes" >&2
      fi
    else
      echo "$(date) ERROR: pg_dump falló" >&2
    fi
    find /respaldos -type f -mtime +"${RETENCION_DIAS}" -delete
    sleep 3600 & wait $!   # no repetir dentro de la misma hora
  fi
  sleep 300 & wait $!
done
