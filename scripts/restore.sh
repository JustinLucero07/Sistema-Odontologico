#!/usr/bin/env bash
#
# Restauración. Pide confirmación escrita porque sobrescribe la base en uso.
#
#   ./scripts/restore.sh backups/odonto-20260920-120000.dump
#
set -Eeuo pipefail

DUMP="${1:-}"
[[ -f "$DUMP" ]] || { echo "Uso: $0 <archivo.dump>" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_URL="$(grep -E '^DATABASE_URL=' "$ROOT/backend/.env" | head -1 | cut -d= -f2-)"
CLEAN="${DB_URL#*://}"; CREDS="${CLEAN%%@*}"; HOSTPART="${CLEAN#*@}"
DB_USER="${CREDS%%:*}"; export PGPASSWORD="${CREDS#*:}"
HOSTPORT="${HOSTPART%%/*}"; DB_NAME="${HOSTPART#*/}"; DB_NAME="${DB_NAME%%\?*}"
DB_HOST="${HOSTPORT%%:*}"; DB_PORT="${HOSTPORT#*:}"; [[ "$DB_PORT" == "$DB_HOST" ]] && DB_PORT=5432

echo "Se va a SOBRESCRIBIR la base «$DB_NAME» en $DB_HOST:$DB_PORT"
echo "con el contenido de $DUMP."
echo
read -r -p "Escriba el nombre de la base para confirmar: " TYPED
[[ "$TYPED" == "$DB_NAME" ]] || { echo "Cancelado."; exit 1; }

# --clean --if-exists deja la base en el estado del volcado, sin restos de
# tablas que se hayan creado después.
pg_restore --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
           --clean --if-exists --no-owner --no-privileges "$DUMP"
echo "Restauración terminada."
