#!/bin/sh
# Copia los respaldos a la nube, CIFRADOS, todos los días.
# Corre en el contenedor «respaldo-externo» (imagen oficial de rclone).
#
#  - Sube los respaldos nuevos de /respaldos al remoto «nube-cifrada» (rclone
#    cifra nombres y contenido antes de que salgan del servidor).
#  - Borra en la nube lo que tenga más de RETENCION_EXTERNA_DIAS días.
#  - Deja el resultado en /estado/externo.txt para «odonto estado».
#
# Sin configurar (sin /config/rclone/rclone.conf con el remoto «nube-cifrada»)
# no hace nada: espera. Se configura con «odonto nube-configurar».
set -u
trap 'echo "Respaldo externo detenido."; exit 0' TERM INT
REMOTO="nube-cifrada:"
estado() { mkdir -p /estado; echo "$1 $(date '+%Y-%m-%d %H:%M') $2" > /estado/externo.txt; }

subir() {
  if ! rclone listremotes 2>/dev/null | grep -qx "nube-cifrada:"; then
    echo "$(date) Respaldo externo SIN CONFIGURAR: ejecute «odonto nube-configurar»."
    estado "SIN_CONFIGURAR" "-"
    return 1
  fi
  echo "$(date) Subiendo respaldos a la nube (cifrados)…"
  if rclone copy /respaldos "$REMOTO" --exclude "*.SOSPECHOSO" --transfers 2 --retries 5 --low-level-retries 10 --stats-one-line -q; then
    rclone delete "$REMOTO" --min-age "${RETENCION_EXTERNA_DIAS}d" -q || true
    N=$(rclone lsf "$REMOTO" 2>/dev/null | grep -c "\.dump$")
    echo "$(date) OK: respaldos en la nube: $N"
    estado "OK" "$N respaldos en la nube"
  else
    echo "$(date) ERROR: no se pudo subir a la nube" >&2
    estado "ERROR" "falló la subida, ver «odonto logs respaldo-externo»"
    return 1
  fi
}

if [ "${1:-}" = "ahora" ]; then subir; exit $?; fi

echo "Respaldo externo activo: cada día a las ${HORA_RESPALDO_EXTERNO}:30, retención ${RETENCION_EXTERNA_DIAS} días."
rclone listremotes 2>/dev/null | grep -qx "nube-cifrada:" || { echo "Aún sin configurar: ejecute «odonto nube-configurar»."; estado "SIN_CONFIGURAR" "-"; }
while true; do
  # A la media hora de la hora indicada: el respaldo local (a la hora en punto) ya terminó.
  if [ "$(date +%H)" = "${HORA_RESPALDO_EXTERNO}" ] && [ "$(date +%M)" -ge 30 ]; then
    subir
    sleep 3600 & wait $!
  fi
  sleep 300 & wait $!
done
