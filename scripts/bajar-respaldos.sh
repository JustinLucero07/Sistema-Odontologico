#!/usr/bin/env bash
# Baja a TU COMPUTADORA los respaldos de un servidor (VPS) del sistema.
# Se ejecuta en tu computadora (Linux o Mac), no en el servidor.
#
#   Bajar ahora:
#     ./bajar-respaldos.sh root@203.0.113.10
#
#   Bajar de otro cliente a otra carpeta:
#     ./bajar-respaldos.sh root@clinica2.com ~/Respaldos/Clinica2
#
#   Programarlo para que baje solo todos los días a las 09:00
#   (si la computadora está apagada a esa hora, lo hace al encenderla):
#     ./bajar-respaldos.sh root@203.0.113.10 --programar
#
# Solo baja lo nuevo (rsync), verifica cada respaldo de la base y guarda
# los últimos DIAS_LOCALES días (por defecto 60).

set -euo pipefail

SERVIDOR="${1:-}"
[ -n "$SERVIDOR" ] || { sed -n '2,17p' "$0"; exit 1; }
shift
DESTINO="$HOME/Respaldos-Odonto/$(printf '%s' "${SERVIDOR#*@}" | tr -c 'A-Za-z0-9.-' '_')"
PROGRAMAR=0
for a in "$@"; do
  case "$a" in
    --programar) PROGRAMAR=1 ;;
    *) DESTINO="$a" ;;
  esac
done
RUTA_REMOTA="${RUTA_REMOTA:-/opt/odonto/infra/respaldos/}"
DIAS_LOCALES="${DIAS_LOCALES:-60}"
# Opciones extra de SSH, por ejemplo otro puerto o llave: SSH_OPCIONES="-p 2222 -i ~/.ssh/vps"
SSH_OPCIONES="${SSH_OPCIONES:-}"

if [ "$PROGRAMAR" = 1 ]; then
  YO="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  ENTORNO="DIAS_LOCALES=$DIAS_LOCALES SSH_OPCIONES='$SSH_OPCIONES'"
  LINEA="0 9 * * * $ENTORNO \"$YO\" $SERVIDOR \"$DESTINO\" >> \"$DESTINO/bajadas.log\" 2>&1"
  mkdir -p "$DESTINO"
  # Reemplaza una programación anterior del mismo servidor, si la había, y
  # agrega dos líneas: a diario a las 09:00 y al encender la computadora
  # (por si a esa hora estaba apagada).
  # (sin tareas previas, «crontab -l» falla y «grep» no encuentra nada: no es un error)
  ( { crontab -l 2>/dev/null || true; } | { grep -vF "\"$YO\" $SERVIDOR " || true; } ; echo "$LINEA"
    echo "@reboot sleep 120; $ENTORNO \"$YO\" $SERVIDOR \"$DESTINO\" >> \"$DESTINO/bajadas.log\" 2>&1" ) | crontab -
  echo "✔ Programado: todos los días a las 09:00 y al encender la computadora."
  echo "  Carpeta: $DESTINO   ·   Registro: $DESTINO/bajadas.log"
  echo "  Para quitarlo: crontab -e  (y borre las líneas de este servidor)"
  exit 0
fi

mkdir -p "$DESTINO"
echo "$(date '+%F %T') Bajando respaldos de $SERVIDOR a $DESTINO …"
# Solo lo que falta; si se corta la conexión, la próxima vez continúa.
rsync -a --partial --ignore-existing --include 'odonto-*.dump' --include 'archivos-*.tar.gz' --exclude '*' \
  -e "ssh -o BatchMode=yes -o ConnectTimeout=20 $SSH_OPCIONES" "$SERVIDOR:$RUTA_REMOTA" "$DESTINO/"

# Verificación: cada volcado de la base debe tener la tabla de pacientes.
MALOS=0
if command -v pg_restore >/dev/null 2>&1; then
  for f in "$DESTINO"/odonto-*.dump; do
    [ -e "$f" ] || continue
    [ -e "$f.ok" ] && continue
    if pg_restore -l "$f" 2>/dev/null | grep -q "TABLE DATA public patients"; then touch "$f.ok"; else echo "✘ Respaldo dañado: $f"; MALOS=$((MALOS + 1)); fi
  done
else
  # Sin PostgreSQL instalado se comprueba al menos la firma del archivo.
  for f in "$DESTINO"/odonto-*.dump; do
    [ -e "$f" ] || continue
    head -c 5 "$f" | grep -q "PGDMP" || { echo "✘ No parece un respaldo válido: $f"; MALOS=$((MALOS + 1)); }
  done
fi

# Limpieza local (en el servidor y en la nube rigen sus propias retenciones).
find "$DESTINO" -maxdepth 1 -type f \( -name 'odonto-*' -o -name 'archivos-*' \) -mtime +"$DIAS_LOCALES" -delete

N=$(ls "$DESTINO"/odonto-*.dump 2>/dev/null | wc -l)
ULTIMO=$(ls -t "$DESTINO"/odonto-*.dump 2>/dev/null | head -1)
echo "$(date '+%F %T') ✔ $N respaldos en esta computadora. Último: $(basename "${ULTIMO:-ninguno}")  ·  $(du -sh "$DESTINO" | cut -f1)"
[ "$MALOS" = 0 ] || exit 2
